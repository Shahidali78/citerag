"""Content-free request telemetry; never serializes provider exceptions or prompts."""
from contextlib import contextmanager, closing
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import json
import logging
import math
import sqlite3
import time
from uuid import uuid4
from . import config

logger = logging.getLogger('citerag.metrics')

@dataclass
class Trace:
    request_id: str = field(default_factory=lambda: str(uuid4()))
    stages: dict = field(default_factory=dict)
    models: dict = field(default_factory=dict)
    usage: dict = field(default_factory=dict)
    retrieval_mode: str | None = None
    retrieved_count: int = 0
    selected_count: int = 0

    @contextmanager
    def timed(self, stage: str):
        started = time.perf_counter()
        try:
            yield
        finally:
            self.stages[stage] = self.stages.get(stage, 0) + time.perf_counter()-started

    def record_usage(self, stage, response, model):
        resolved = getattr(response, 'model', None)
        self.models[stage] = resolved if isinstance(resolved, str) else model
        usage = getattr(response, 'usage', None)
        def integer(*names):
            for name in names:
                value = usage.get(name) if isinstance(usage, dict) else getattr(usage, name, None)
                if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                    return value
            return None
        current = {'input_tokens': integer('input_tokens', 'prompt_tokens'), 'output_tokens': integer('output_tokens'), 'total_tokens': integer('total_tokens')}
        previous = self.usage.get(stage, {})
        self.usage[stage] = {key: (previous.get(key) or 0) + value if value is not None else previous.get(key) for key,value in current.items()}

    def snapshot(self):
        def price(name):
            raw = getattr(config, name)
            try:
                value = float(raw)
                return value if math.isfinite(value) and value >= 0 else None
            except (TypeError, ValueError):
                return None
        prices = {'embedding': (price('EMBEDDING_PRICE'), 0), 'generation': (price('CHAT_INPUT_PRICE'), price('CHAT_OUTPUT_PRICE')), 'judge': (price('CHAT_INPUT_PRICE'), price('CHAT_OUTPUT_PRICE'))}
        cost = 0.0
        complete = bool(self.usage)
        for stage, usage in self.usage.items():
            input_price, output_price = prices.get(stage, (None, None))
            input_tokens = usage.get('input_tokens')
            output_tokens = usage.get('output_tokens')
            if input_price is None or input_tokens is None or (stage in {'generation', 'judge'} and (output_price is None or output_tokens is None)):
                complete = False
            else:
                cost += (input_tokens*input_price + (output_tokens or 0)*output_price) / 1_000_000
        return {'request_id': self.request_id, 'stages_seconds': self.stages, 'models': self.models, 'usage': self.usage,
                'estimated_cost_usd': round(cost, 8) if complete else None, 'retrieval_mode': self.retrieval_mode,
                'retrieved_count': self.retrieved_count, 'selected_count': self.selected_count}

active_trace: ContextVar[Trace | None] = ContextVar('citerag_trace', default=None)

def trace() -> Trace:
    return active_trace.get() or Trace()

def metrics_db():
    config.ensure_data_dirs()
    db = sqlite3.connect(config.SQLITE_PATH + '.metrics', timeout=10)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS metrics (id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, request_id TEXT NOT NULL, endpoint TEXT NOT NULL, status INTEGER NOT NULL, latency_seconds REAL NOT NULL, data TEXT NOT NULL)')
    db.execute('CREATE INDEX IF NOT EXISTS metrics_created_at ON metrics(created_at)')
    db.commit()
    return db

def save_metric(record: dict):
    # Only internally constructed allowlisted fields are persisted.
    cutoff = (datetime.now(timezone.utc)-timedelta(days=config.METRICS_RETENTION_DAYS)).isoformat()
    with closing(metrics_db()) as db, db:
        db.execute('DELETE FROM metrics WHERE created_at < ?', (cutoff,))
        db.execute('INSERT INTO metrics (created_at,request_id,endpoint,status,latency_seconds,data) VALUES (?,?,?,?,?,?)',
                   (record['timestamp'], record['request_id'], record['endpoint'], record['status'], record['latency_seconds'], json.dumps(record)))
    logger.info(json.dumps(record, separators=(',', ':')))

def monitoring():
    cutoff = (datetime.now(timezone.utc)-timedelta(days=config.METRICS_RETENTION_DAYS)).isoformat()
    with closing(metrics_db()) as db, db:
        db.execute('DELETE FROM metrics WHERE created_at < ?', (cutoff,))
        aggregate = dict(db.execute('SELECT COUNT(*) total_requests, AVG(latency_seconds) average_latency_seconds, SUM(CASE WHEN status >= 400 THEN 1 ELSE 0 END) errors FROM metrics').fetchone())
        records = [json.loads(row['data']) for row in db.execute('SELECT data FROM metrics ORDER BY id DESC LIMIT 1000')]
    usage = {'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0}
    modes = {}
    costs = []
    known_usage = 0
    for record in records:
        mode = record.get('retrieval_mode')
        if mode:
            modes[mode] = modes.get(mode, 0)+1
        for stage in record.get('usage', {}).values():
            if stage.get('total_tokens') is not None:
                known_usage += 1
            for key in usage:
                usage[key] += stage.get(key) or 0
        if record.get('estimated_cost_usd') is not None:
            costs.append(record['estimated_cost_usd'])
    return {**aggregate, 'average_latency_seconds': aggregate['average_latency_seconds'] or 0,
            'error_rate': (aggregate['errors'] or 0)/max(1, aggregate['total_requests']), 'tokens': usage,
            'usage_observations': known_usage, 'estimated_cost_usd': round(sum(costs), 8) if costs else None,
            'costed_requests': len(costs), 'retrieval_configurations': modes, 'retention_days': config.METRICS_RETENTION_DAYS,
            'sampled_requests': len(records), 'aggregation_note': 'Request count and latency span retained rows. Token/cost/configuration aggregates cover the latest 1000 rows; missing usage and prices are excluded.', 'recent': records[:50]}
