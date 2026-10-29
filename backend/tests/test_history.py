import pytest
from fastapi.testclient import TestClient
from app.eval.history import archive_run, read_run, list_runs
from app.main import app

def test_immutable_history_and_safe_identifiers():
    report={'created_at':'2026-10-29','mode':'openai','summary':{'source_recall_at_k':1},'results':[]}
    first=archive_run(report,'first');second=archive_run(report,'second')
    assert first!=second and read_run(first)['label']=='first'
    assert len(list_runs())==2
    with pytest.raises(ValueError):read_run('../../.env')
    with TestClient(app) as api:
        assert len(api.get('/evaluations/runs').json())==2
        assert api.get('/evaluations/runs/'+first).json()['mode']=='openai'
        assert api.get('/evaluations/runs/not-a-run').status_code==404

def test_chroma_http_server_not_exposed():
    assert not any(path.startswith('/api/v2') for path in app.openapi()['paths'])
