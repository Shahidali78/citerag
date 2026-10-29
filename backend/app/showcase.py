"""Read-only, allowlisted public artifacts. Never reads runtime databases."""
from functools import lru_cache
import json
from uuid import NAMESPACE_URL, uuid5
from fastapi import HTTPException
from . import config
from .schemas import ChatResponse

REPORTS = {str(uuid5(NAMESPACE_URL, 'citerag-heldout-' + mode)): mode
           for mode in ('dense', 'hybrid', 'hybrid_rerank')}


@lru_cache(maxsize=4)
def report(mode='hybrid'):
    if mode not in {'dense', 'hybrid', 'hybrid_rerank'}:
        raise HTTPException(404, 'Public report not found')
    path = config.BASE_DIR.parent / 'docs' / 'heldout' / 'v1' / f'answers-{mode}.json'
    return json.loads(path.read_text(encoding='utf-8'))


def runs():
    keys = ['created_at', 'mode', 'examples', 'summary', 'retrieval_configuration', 'evaluation_kind', 'dataset_split']
    return [{**{key: report(mode).get(key) for key in keys}, 'run_id': run_id,
             'label': f'Saved real OpenAI holdout: {mode}'} for run_id, mode in REPORTS.items()]


def read_run(run_id):
    if run_id not in REPORTS:
        raise HTTPException(404, 'Public report not found')
    return report(REPORTS[run_id])


def documents():
    chunks = {c['chunk_id']: c for row in report()['results'] for c in row['retrieved_chunks']}
    grouped = {}
    for chunk in chunks.values():
        key = chunk['document_id']
        grouped.setdefault(key, {'id': key, 'filename': chunk['filename'], 'chunks': 0,
                                 'created_at': report()['created_at']})['chunks'] += 1
    return list(grouped.values())


def questions():
    return [row['question'] for row in report()['results'] if row['answerable']][:6]


def answer(question):
    for row in report()['results']:
        if row['question'].casefold() == question.casefold():
            response = {key: row[key] for key in ChatResponse.model_fields if key in row}
            # Historical billing/latency is not new request usage.
            response['telemetry'] = {'showcase': True, 'source': 'Saved real OpenAI hybrid holdout response'}
            return ChatResponse(**response)
    raise HTTPException(422, 'Choose a listed sample question. Showcase replays saved responses; it does not generate answers.')
