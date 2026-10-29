"""Immutable, local-only evaluation history; IDs never become arbitrary paths."""
import json
import re
from uuid import uuid4
from .. import config

def archive_run(report: dict, label: str = 'evaluation') -> str:
    folder = config.EVALUATION_HISTORY_PATH
    folder.mkdir(parents=True, exist_ok=True)
    run_id = str(uuid4())
    value = {**report, 'run_id': run_id, 'label': label}
    with (folder / f'{run_id}.json').open('x', encoding='utf-8') as handle:
        json.dump(value, handle, indent=2)
    return run_id

def read_run(run_id: str):
    if not re.fullmatch(r'[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}', run_id):
        raise ValueError('Invalid run identifier')
    return json.loads((config.EVALUATION_HISTORY_PATH / f'{run_id}.json').read_text(encoding='utf-8'))

def list_runs():
    runs = []
    for path in config.EVALUATION_HISTORY_PATH.glob('*.json'):
        try:
            report = read_run(path.stem)
            runs.append({key: report.get(key) for key in ['run_id', 'label', 'created_at', 'updated_at', 'mode', 'examples', 'top_k', 'summary', 'retrieval_configuration', 'evaluation_kind', 'dataset_split', 'evaluation_protocol']})
        except (ValueError, OSError):
            continue
    return sorted(runs, key=lambda row: row.get('updated_at') or row.get('created_at') or '', reverse=True)
