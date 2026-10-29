"""Opt-in live integration check. Uploads missing fixtures and makes two paid queries."""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import config
from app.provider import demo_enabled
from app.store import collection


def make_pdf(path: Path):
    writer = PdfWriter()
    font = writer._add_object(DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')}))
    texts = ['The document review window is 14 days.',
             'The support escalation code is ORCHID-42. The support desk opens at 09:00 UTC on weekdays.']
    for text in texts:
        page = writer.add_blank_page(width=612, height=792)
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): font})})
        stream = DecodedStreamObject()
        stream.set_data(f'BT /F1 12 Tf 50 740 Td ({text}) Tj ET'.encode('ascii'))
        page[NameObject('/Contents')] = writer._add_object(stream)
    writer.write(path)
    assert [p.extract_text() for p in PdfReader(path).pages] == texts


def run(base_url: str, output: Path):
    if demo_enabled():
        raise RuntimeError('Disable demo mode before this live check; no automatic fallback is permitted.')
    root = config.BASE_DIR
    make_pdf(root / 'evals' / 'verification.pdf')
    with httpx.Client(base_url=base_url, timeout=180) as api:
        health = api.get('/health').json()
        assert health['mode'] == 'openai' and health['openai_configured']
        existing = {d['filename']: d for d in api.get('/documents').json()}
        uploads = []
        for name in ['sample.md', 'operations.txt', 'verification.pdf']:
            if name in existing:
                doc = existing[name]
                status = 'already indexed'
            else:
                response = api.post('/documents', files={'file': (name, (root / 'evals' / name).read_bytes())})
                response.raise_for_status()
                doc, status = response.json(), 'indexed via API'
            uploads.append({'filename': name, 'status': status, **doc})
            print(f"{name}: {status}, {doc['chunks']} chunks", flush=True)

        stored = collection().get(include=['documents', 'metadatas', 'embeddings'])
        dimensions = {len(v) for v in stored['embeddings']}
        assert dimensions == {1536}, 'Expected default text-embedding-3-small vectors'
        pdf_pages = sorted(m['page'] for m in stored['metadatas'] if m['filename'] == 'verification.pdf')
        assert pdf_pages == [1, 2]
        known = {chunk_id: (text, meta) for chunk_id, text, meta in zip(stored['ids'], stored['documents'], stored['metadatas'])}
        checks = []
        for question, filename, page, fact in [
            ('What is the maximum upload size?', 'sample.md', 1, '20'),
            ('What is the support escalation code?', 'verification.pdf', 2, 'ORCHID-42')]:
            response = api.post('/chat', json={'question': question, 'top_k': 5})
            response.raise_for_status()
            answer = response.json()
            assert fact in answer['answer'] and answer['citations']
            assert any(c['filename'] == filename and c['page'] == page for c in answer['citations'])
            for citation in answer['citations']:
                text, meta = known[citation['chunk_id']]
                assert text == citation['snippet'] and meta['filename'] == citation['filename'] and meta['page'] == citation['page']
                assert citation['marker'] in answer['answer']
            checks.append({'question': question, **answer})
            print(f'Grounded answer and stored citation verified: {question}', flush=True)
        cors = api.options('/chat', headers={'Origin': 'http://localhost:3000', 'Access-Control-Request-Method': 'POST'})
        assert cors.headers.get('access-control-allow-origin') == 'http://localhost:3000'
    report = {'created_at': datetime.now(timezone.utc).isoformat(), 'mode': 'openai', 'chat_model': config.CHAT_MODEL,
              'embedding_model': config.EMBEDDING_MODEL, 'embedding_dimensions': sorted(dimensions),
              'uploads': uploads, 'pdf_pages': pdf_pages, 'stored_chunk_ids': sorted(known), 'checks': checks, 'cors': 'passed'}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(f'Live verification saved to {output}', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://localhost:8000')
    parser.add_argument('--output', type=Path, default=Path('../docs/live-integration.json'))
    args = parser.parse_args()
    run(args.base_url, args.output)
