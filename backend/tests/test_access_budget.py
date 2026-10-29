from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from app import config, main, budget
from app.provider import BudgetedClient, get_client

TOKEN = 'fixture-only-owner-token-not-for-deployment'
HEADERS = {'Authorization': f'Bearer {TOKEN}'}


@pytest.mark.parametrize('method,path', [('get','/documents'), ('get','/monitoring'), ('get','/evaluations'),
    ('get','/evaluations/runs'), ('get','/docs'), ('get','/openapi.json'), ('get','/auth'),
    ('post','/chat'), ('post','/documents'), ('delete','/documents/anything')])
def test_live_routes_deny_anonymous_before_body_or_provider(method, path, monkeypatch):
    factory = Mock(side_effect=AssertionError('No provider call allowed'))
    monkeypatch.setattr(main, 'get_client', factory)
    with TestClient(main.app) as api:
        response = getattr(api, method)(path)
    assert response.status_code == 401
    factory.assert_not_called()


def test_live_fails_closed_without_configured_secret(monkeypatch):
    monkeypatch.setattr(config, 'ACCESS_TOKEN', '')
    with TestClient(main.app) as api:
        assert api.get('/health').status_code == 200
        assert api.get('/session').json()['live_configured'] is False
        assert api.get('/documents', headers=HEADERS).status_code == 503


def test_wrong_credentials_cannot_read_owner_data():
    with TestClient(main.app) as api:
        assert api.get('/documents', headers={'Authorization': 'Bearer wrong'}).status_code == 401
        assert api.get('/documents', headers=HEADERS).status_code == 200
        assert api.get('/session', headers=HEADERS).json()['authenticated'] is True


def test_anonymous_requests_do_not_allocate_private_storage():
    from pathlib import Path
    with TestClient(main.app) as api:
        assert api.get('/documents').status_code == 401
        assert api.post('/chat', json={'question':'anything'}).status_code == 401
    assert not Path(config.SQLITE_PATH).exists()
    assert not Path(config.SQLITE_PATH + '.metrics').exists()
    assert not Path(config.SQLITE_PATH + '.budget').exists()


def test_showcase_replays_without_provider_or_private_store(monkeypatch):
    monkeypatch.setattr(config, 'ACCESS_MODE', 'showcase')
    monkeypatch.setattr(main, 'list_documents', Mock(side_effect=AssertionError('Private data read')))
    monkeypatch.setattr(main, 'get_client', Mock(side_effect=AssertionError('Provider call')))
    with TestClient(main.app) as api:
        questions = api.get('/showcase/questions').json()
        result = api.post('/chat', json={'question': questions[0]}).json()
        assert result['telemetry']['showcase'] is True
        assert result['citations']
        assert {doc['filename'] for doc in api.get('/documents').json()} == {'verification.pdf', 'operations.txt', 'sample.md'}
        assert api.post('/chat', json={'question': 'Generate something new'}).status_code == 422
        assert api.get('/evaluations').json()['examples'] == 40
        assert api.get('/evaluations/runs/not-a-public-id').status_code == 404
        assert api.get('/monitoring').status_code == 403
        assert api.post('/documents', files={'file': ('x.txt', b'private')}).status_code == 403
        assert api.delete('/documents/anything').status_code == 403
    with pytest.raises(RuntimeError, match='Showcase'):
        get_client()


def test_paid_request_quota_survives_new_client(monkeypatch):
    monkeypatch.setattr(config, 'DAILY_REQUEST_LIMIT', 1)
    with TestClient(main.app, headers=HEADERS) as api:
        assert api.post('/chat', json={'question':'first'}).status_code == 200
    with TestClient(main.app, headers=HEADERS) as api:
        response = api.post('/chat', json={'question':'second'})
        assert response.status_code == 429
        assert 'Daily live usage allowance' in response.text
    assert budget.summary()['reserved']['requests'] == 1


def test_concurrent_quota_reservations_are_atomic(monkeypatch):
    monkeypatch.setattr(config, 'DAILY_REQUEST_LIMIT', 1)
    def request(_):
        try:
            budget.reserve(requests=1)
            return True
        except HTTPException:
            return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sum(pool.map(request, range(2))) == 1


def prices(monkeypatch):
    for name in ['CHAT_INPUT_PRICE', 'CHAT_OUTPUT_PRICE', 'EMBEDDING_PRICE']:
        monkeypatch.setattr(config, name, '1')


def test_output_cap_reservation_and_unknown_usage_are_conservative(monkeypatch):
    prices(monkeypatch)
    monkeypatch.setattr(config, 'MAX_OUTPUT_TOKENS', 100)
    monkeypatch.setattr(config, 'OPENAI_RETRIES', 2)
    upstream = Mock()
    client = BudgetedClient(upstream)
    client.responses.create(input='hello', instructions='facts', model=config.CHAT_MODEL, max_output_tokens=99999)
    args = upstream.responses.create.call_args.kwargs
    assert args['max_output_tokens'] == 100 and args['store'] is False
    before = budget.summary()['reserved']
    assert before['tokens'] == (len('factshello'.encode()) + 512 + 100) * 3
    upstream.embeddings.create.side_effect = RuntimeError('Unknown billed usage')
    with pytest.raises(RuntimeError):
        client.embeddings.create(input=['embed this'], model=config.EMBEDDING_MODEL)
    assert budget.summary()['reserved']['tokens'] > before['tokens']


@pytest.mark.parametrize('kind', ['tokens','usd','missing-price','context'])
def test_budget_denial_happens_before_provider(kind, monkeypatch):
    prices(monkeypatch)
    if kind == 'tokens': monkeypatch.setattr(config, 'DAILY_TOKEN_LIMIT', 1)
    if kind == 'usd': monkeypatch.setattr(config, 'DAILY_USD_LIMIT', .000001)
    if kind == 'missing-price': monkeypatch.setattr(config, 'CHAT_INPUT_PRICE', None)
    if kind == 'context': monkeypatch.setattr(config, 'MAX_CONTEXT_CHARS', 1)
    upstream = Mock()
    with pytest.raises(HTTPException) as error:
        BudgetedClient(upstream).responses.create(input='bounded context', model=config.CHAT_MODEL)
    assert error.value.status_code in {422,429,503}
    upstream.responses.create.assert_not_called()


def test_daily_allowance_resets_at_utc_day_boundary(monkeypatch):
    monkeypatch.setattr(config, 'DAILY_REQUEST_LIMIT', 1)
    monkeypatch.setattr(budget, 'day', lambda: '2026-10-29')
    budget.reserve(requests=1)
    monkeypatch.setattr(budget, 'day', lambda: '2026-10-30')
    budget.reserve(requests=1)
    assert budget.summary()['reserved']['requests'] == 1
