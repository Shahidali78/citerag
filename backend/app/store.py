import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
import chromadb
from contextlib import closing
from . import config
from .provider import demo_enabled

def database() -> sqlite3.Connection:
    config.ensure_data_dirs()
    conn = sqlite3.connect(config.SQLITE_PATH + ('.demo' if demo_enabled() else ''))
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY, filename TEXT NOT NULL, chunks INTEGER NOT NULL, created_at TEXT NOT NULL)")
    conn.execute('CREATE TABLE IF NOT EXISTS query_logs (id INTEGER PRIMARY KEY, question TEXT NOT NULL, retrieved_chunk_ids TEXT NOT NULL, created_at TEXT NOT NULL)')
    conn.commit()
    return conn

def collection():
    config.ensure_data_dirs()
    name = 'citerag_demo' if demo_enabled() else 'citerag'
    return chromadb.PersistentClient(path=config.CHROMA_PATH).get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})

def save_document(document_id: str, filename: str, texts: list[str], pages: list[int], embeddings: list[list[float]]) -> None:
    if not texts or not (len(texts) == len(pages) == len(embeddings)):
        raise ValueError('Text, page, and embedding counts must match and be nonempty')
    ids = [f"{document_id}:{i}" for i in range(len(texts))]
    col = collection()
    try:
        for i in range(0, len(ids), 100):
            col.add(ids=ids[i:i+100], documents=texts[i:i+100], embeddings=embeddings[i:i+100], metadatas=[{"document_id": document_id, "filename": filename, "page": page} for page in pages[i:i+100]])
        with closing(database()) as db, db:
            db.execute("INSERT INTO documents VALUES (?, ?, ?, ?)", (document_id, filename, len(ids), datetime.now(timezone.utc).isoformat()))
    except Exception:
        col.delete(where={"document_id": document_id})
        raise

def list_documents() -> list[dict]:
    with closing(database()) as db, db:
        return [dict(row) for row in db.execute("SELECT * FROM documents ORDER BY created_at DESC")]

def delete_document(document_id: str) -> bool:
    with closing(database()) as db, db:
        exists = db.execute("SELECT 1 FROM documents WHERE id = ?", (document_id,)).fetchone()
        if not exists:
            return False
        collection().delete(where={"document_id": document_id})
        db.execute("DELETE FROM documents WHERE id = ?", (document_id,))
    return True

def log_query(question: str, chunk_ids: list[str]) -> None:
    if not config.LOG_QUERY_TEXT:
        return
    with closing(database()) as db, db:
        db.execute('INSERT INTO query_logs (question, retrieved_chunk_ids, created_at) VALUES (?, ?, ?)', (question, json.dumps(chunk_ids), datetime.now(timezone.utc).isoformat()))

