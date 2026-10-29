"""Local-only, explicitly offline integration server. Never touches owner data."""
import argparse
import os
from pathlib import Path
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--mode', choices=['showcase', 'live'], required=True)
parser.add_argument('--port', type=int, required=True)
parser.add_argument('--data', type=Path, required=True)
args = parser.parse_args()
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
args.data.mkdir(parents=True, exist_ok=True)
# This known token is a test fixture, never a deployment credential.
os.environ.update(CITERAG_ACCESS_MODE=args.mode, CITERAG_DEMO='true', OPENAI_API_KEY='',
    CITERAG_ACCESS_TOKEN='fixture-only-owner-token-not-for-deployment',
    CHROMA_PATH=str(args.data / 'chroma'), SQLITE_PATH=str(args.data / 'metadata.sqlite3'),
    EVALUATION_PATH=str(args.data / 'report.json'), EVALUATION_HISTORY_PATH=str(args.data / 'runs'),
    RATE_LIMIT_REQUESTS='1000', DAILY_REQUEST_LIMIT='1000')

if args.mode == 'live':
    import json
    from app import config
    from app.provider import DemoClient
    from app.eval.history import archive_run
    from app.eval.independent_data import source_catalog
    from app.store import save_document, list_documents
    if not list_documents():
        groups = {}
        for chunk in source_catalog():
            groups.setdefault(chunk['chunk_id'].rsplit(':', 1)[0], []).append(chunk)
        for doc_id, chunks in groups.items():
            vectors = DemoClient().embed(input=[c['text'] for c in chunks]).data
            save_document(doc_id, chunks[0]['filename'], [c['text'] for c in chunks], [c['page'] for c in chunks], [v.embedding for v in vectors])
    root = config.BASE_DIR.parent
    # Display existing genuine reports; do not generate or recalculate metrics.
    config.EVALUATION_PATH.write_text((root / 'docs/heldout/v1/answers-hybrid.json').read_text(encoding='utf-8'), encoding='utf-8')
    if not list(config.EVALUATION_HISTORY_PATH.glob('*.json')):
        for mode in ('dense', 'hybrid', 'hybrid_rerank'):
            archive_run(json.loads((root / f'docs/heldout/v1/answers-{mode}.json').read_text()), f'Saved public sample: {mode}')

import uvicorn
uvicorn.run('app.main:app', host='127.0.0.1', port=args.port, access_log=False)
