from types import SimpleNamespace
from fastapi.testclient import TestClient
import json
from app.main import app
from app import config, main
from app.observability import Trace, monitoring, metrics_db
from app.security import safe_filename, RateLimiter

def test_metrics_privacy_and_request_id(monkeypatch):
    monkeypatch.setattr(main, 'limiter', RateLimiter())
    question = 'PRIVATE_QUESTION_DO_NOT_LOG'
    with TestClient(app) as api:
        r=api.post('/chat',json={'question':question})
        assert r.headers['x-request-id'] == r.json()['telemetry']['request_id']
        report=api.get('/monitoring').json()
    serialized=json.dumps(report)
    assert question not in serialized and 'snippet' not in serialized
    assert report['total_requests'] == 1 and report['recent'][0]['success']
    assert report['estimated_cost_usd'] is None

def test_usage_and_optional_pricing(monkeypatch):
    trace=Trace()
    trace.record_usage('embedding',SimpleNamespace(usage=SimpleNamespace(prompt_tokens=100,total_tokens=100)),'embed')
    trace.record_usage('generation',SimpleNamespace(usage=SimpleNamespace(input_tokens=200,output_tokens=50,total_tokens=250)),'chat')
    assert trace.snapshot()['estimated_cost_usd'] is None
    monkeypatch.setattr(config,'EMBEDDING_PRICE','1')
    monkeypatch.setattr(config,'CHAT_INPUT_PRICE','2')
    monkeypatch.setattr(config,'CHAT_OUTPUT_PRICE','4')
    assert trace.snapshot()['estimated_cost_usd'] == .0007
    empty=Trace(); empty.record_usage('generation',SimpleNamespace(), 'unknown')
    assert empty.snapshot()['usage']['generation']['total_tokens'] is None

def test_rate_limit_and_validation(monkeypatch):
    monkeypatch.setattr(main,'limiter',RateLimiter())
    monkeypatch.setattr(config,'RATE_LIMIT_REQUESTS',1)
    with TestClient(app) as api:
        assert api.post('/chat',json={'question':'hello'}).status_code == 200
        r=api.post('/chat',json={'question':'again'})
        assert r.status_code == 429 and r.headers['retry-after']
        assert api.get('/health').status_code == 200

def test_filename_sanitization():
    assert safe_filename('../private/document.md') == 'document.md'
    assert safe_filename('C:\\private\\document.txt') == 'document.txt'
    assert safe_filename('doc\x00.txt') == 'doc.txt'

def test_legacy_question_logging_disabled():
    from app.store import log_query, database
    log_query('private question',[])
    db=database()
    assert db.execute('SELECT COUNT(*) FROM query_logs').fetchone()[0] == 0
    db.close()

def test_untrusted_origins_and_hosts_are_rejected():
    with TestClient(app) as api:
        assert api.post('/chat',json={'question':'q'},headers={'Origin':'https://untrusted.example'}).status_code==403
        assert api.post('/chat',json={'question':'q'},headers={'Origin':'http://testserver'}).status_code==200
        assert api.get('/health',headers={'Host':'untrusted.example'}).status_code==400

def test_metrics_retention(monkeypatch):
    from app.observability import save_metric
    trace=Trace()
    save_metric({**trace.snapshot(),'timestamp':'2000-01-01T00:00:00+00:00','endpoint':'/chat','status':200,'latency_seconds':1})
    assert monitoring()['total_requests']==0

def test_chunked_upload_body_is_bounded(monkeypatch):
    monkeypatch.setattr(config,'MAX_UPLOAD_BYTES',3)
    header=b'--boundary\r\nContent-Disposition: form-data; name="file"; filename="a.txt"\r\n\r\n'
    with TestClient(app) as api:
        response=api.post('/documents',content=iter([header,b'x'*(1024*1024+10),b'\r\n--boundary--\r\n']),headers={'Content-Type':'multipart/form-data; boundary=boundary'})
        assert response.status_code==413

def test_health_docs_and_monitoring_do_not_inflate_request_metrics():
    with TestClient(app) as api:
        for path in ['/health','/docs','/openapi.json','/monitoring']:
            assert api.get(path).status_code==200
        assert api.get('/monitoring').json()['total_requests']==0
