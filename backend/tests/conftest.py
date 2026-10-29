import pytest
from app import config

@pytest.fixture(autouse=True)
def isolated_data(tmp_path, monkeypatch):
    monkeypatch.setattr(config, 'ACCESS_MODE', 'live')
    monkeypatch.setattr(config, 'ACCESS_TOKEN', 'fixture-only-owner-token-not-for-deployment')
    monkeypatch.setattr(config, 'DAILY_REQUEST_LIMIT', 1000)
    monkeypatch.setenv('CITERAG_DEMO', 'true')
    monkeypatch.setattr(config, 'CHROMA_PATH', str(tmp_path / 'chroma'))
    monkeypatch.setattr(config, 'SQLITE_PATH', str(tmp_path / 'metadata.sqlite3'))
    monkeypatch.setattr(config, 'EVALUATION_PATH', tmp_path / 'results.json')
    monkeypatch.setattr(config, 'EVALUATION_HISTORY_PATH', tmp_path / 'runs')
    from app import main
    from app.security import RateLimiter
    monkeypatch.setattr(main, 'limiter', RateLimiter())
