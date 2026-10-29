"""Conservative UTC-day reservations, serialized with SQLite write transactions.

Reservations are not refunded: failed/unknown/retried calls may still be billed.
The guard is an estimate using owner-configured prices, not a provider hard cap.
"""
from contextlib import closing
from datetime import datetime, timezone
import math
import sqlite3
from fastapi import HTTPException
from . import config


def day():
    return datetime.now(timezone.utc).date().isoformat()


def connection():
    config.ensure_data_dirs()
    db = sqlite3.connect(config.SQLITE_PATH + '.budget', timeout=10)
    db.row_factory = sqlite3.Row
    db.execute('CREATE TABLE IF NOT EXISTS daily (day TEXT PRIMARY KEY, requests INTEGER NOT NULL DEFAULT 0, tokens INTEGER NOT NULL DEFAULT 0, usd REAL NOT NULL DEFAULT 0)')
    db.commit()
    return db


def reserve(*, requests=0, tokens=0, usd=0.0):
    stamp = day()
    with closing(connection()) as db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('DELETE FROM daily WHERE day < date(?, "-31 days")', (stamp,))
        db.execute('INSERT OR IGNORE INTO daily(day) VALUES (?)', (stamp,))
        row = db.execute('SELECT * FROM daily WHERE day=?', (stamp,)).fetchone()
        if (row['requests'] + requests > config.DAILY_REQUEST_LIMIT
                or row['tokens'] + tokens > config.DAILY_TOKEN_LIMIT
                or row['usd'] + usd > config.DAILY_USD_LIMIT):
            raise HTTPException(429, 'Daily live usage allowance reached. Resets at UTC midnight.')
        db.execute('UPDATE daily SET requests=requests+?, tokens=tokens+?, usd=usd+? WHERE day=?',
                   (requests, tokens, usd, stamp))
        db.commit()


def summary():
    with closing(connection()) as db:
        row = db.execute('SELECT requests,tokens,usd FROM daily WHERE day=?', (day(),)).fetchone()
    return {'utc_day': day(), 'reserved': dict(row) if row else {'requests': 0, 'tokens': 0, 'usd': 0},
            'limits': {'requests': config.DAILY_REQUEST_LIMIT, 'tokens': config.DAILY_TOKEN_LIMIT, 'usd': config.DAILY_USD_LIMIT},
            'note': 'Conservative reservations, not provider charges. Failed calls remain reserved; prices are owner configured.'}


def reserve_call(stage, payload):
    if stage == 'generation':
        if len(payload.get('input', '')) > config.MAX_CONTEXT_CHARS:
            raise HTTPException(422, 'Selected context exceeds the configured live context limit.')
        names = ('CHAT_INPUT_PRICE', 'CHAT_OUTPUT_PRICE')
        text = payload.get('instructions', '') + payload.get('input', '')
        output = payload['max_output_tokens']
    else:
        names = ('EMBEDDING_PRICE',)
        text = ''.join(payload['input'])
        output = 0
    try:
        prices = [float(getattr(config, name)) for name in names]
        if not all(math.isfinite(price) and price > 0 for price in prices):
            raise ValueError()
    except (TypeError, ValueError):
        raise HTTPException(503, 'Configure positive, current model prices before enabling paid calls.')
    # UTF-8 bytes overbound BPE tokens; include framing and the SDK retry ceiling.
    input_bound = len(text.encode('utf-8')) + 512
    attempts = 1 + config.OPENAI_RETRIES
    cost = (input_bound * prices[0] + output * (prices[-1] if output else 0)) / 1_000_000
    reserve(tokens=(input_bound + output) * attempts, usd=cost * attempts)
