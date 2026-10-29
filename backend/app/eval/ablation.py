"""Ablations reuse query embeddings, never invented answer scores or cached LLM latency."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import statistics
import time
from uuid import uuid4
from .. import config
from ..provider import get_client, demo_enabled
from ..retrieval import retrieve, RetrievalOptions
from ..store import collection, list_documents
from ..rag import answer_question
from ..observability import Trace, active_trace
from .metrics import source_recall, source_precision, reciprocal_rank, evidence_coverage, lexical_f1, citation_validity, support_accuracy
from .run import judge_quality
from .history import archive_run

def fingerprint(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()

def average(rows: list[dict], keys: list[str]):
    return {key: round(statistics.mean(row[key] for row in rows if row.get(key) is not None), 4) if any(row.get(key) is not None for row in rows) else None for key in keys}

def retrieval_row(example, selected, diagnostics, seconds):
    sources = [c.metadata['filename'] for c in selected]
    expected = example.get('expected_sources', [])
    return {'question': example['question'], 'source_recall_at_k': source_recall(sources, expected),
            'source_precision_at_k': source_precision(sources, expected), 'mrr': reciprocal_rank(sources, expected),
            'expected_evidence_coverage': evidence_coverage(example.get('expected_evidence', ''), [c.text for c in selected]),
            'selected_count': len(selected), 'retrieval_seconds': seconds, 'selected_chunk_ids': [c.chunk_id for c in selected],
            'diagnostics': [c.diagnostic() for c in diagnostics]}

def retrieval_run(examples, vectors, options):
    rows = []
    for example, vector in zip(examples, vectors):
        started = time.perf_counter()
        selected, candidates, info = retrieve(example['question'], vector, options)
        rows.append(retrieval_row(example, selected, candidates, time.perf_counter()-started))
    return rows

def execute(dataset: Path, output: Path, answers: bool = False, judge: bool = False):
    if demo_enabled():
        raise ValueError('A real ablation requires CITERAG_DEMO=false; no fallback is permitted')
    examples = [json.loads(line) for line in dataset.read_text(encoding='utf-8').splitlines() if line.strip()]
    stored = collection().get(include=['documents', 'metadatas'])
    if not examples or not stored['ids']:
        raise ValueError('Dataset and indexed corpus must not be empty')
    corpus = sorted(zip(stored['ids'], stored['documents'], stored['metadatas']))
    corpus_hash, dataset_hash = fingerprint(corpus), fingerprint(examples)
    client = get_client()
    output.mkdir(parents=True, exist_ok=False)
    cache_path = Path(config.CHROMA_PATH).parent / ('query-vectors-'+dataset_hash[:16]+'.json')
    cache_key = fingerprint({'questions': [e['question'] for e in examples], 'model': config.EMBEDDING_MODEL})
    cache = json.loads(cache_path.read_text(encoding='utf-8')) if cache_path.exists() else {}
    if cache.get('key') != cache_key:
        started = time.perf_counter()
        response = client.embeddings.create(model=config.EMBEDDING_MODEL, input=[e['question'] for e in examples])
        metric = Trace()
        metric.record_usage('embedding', response, config.EMBEDDING_MODEL)
        cache = {'key': cache_key, 'vectors': [item.embedding for item in sorted(response.data, key=lambda item: item.index)],
                 'embedding_batch_seconds': time.perf_counter()-started, 'telemetry': metric.snapshot()}
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(cache), encoding='utf-8')
    vectors = cache['vectors']
    if len(vectors) != len(examples):
        raise ValueError('Query vector cache length mismatch')
    baseline = retrieval_run(examples, vectors, RetrievalOptions('dense', 20, 5, 0))
    trials = []
    for threshold in [0, .1, .2, .25, .3, .35, .4, .45, .5, .55, .6, .65, .7, .75, .8]:
        rows = retrieval_run(examples, vectors, RetrievalOptions('hybrid_rerank', 20, 5, threshold))
        eligible = all(row['source_recall_at_k'] >= original['source_recall_at_k'] and row['expected_evidence_coverage'] >= original['expected_evidence_coverage'] for row,original in zip(rows, baseline))
        trials.append({'threshold': threshold, 'preserves_every_question_source_recall_and_evidence_coverage': eligible,
                       **average(rows, ['source_recall_at_k', 'source_precision_at_k', 'expected_evidence_coverage', 'selected_count'])})
    eligible = [trial for trial in trials if trial['preserves_every_question_source_recall_and_evidence_coverage']]
    best = max(eligible, key=lambda trial: (trial['source_precision_at_k'], trial['threshold'])) if eligible else trials[0]
    options_list = [RetrievalOptions('dense', 20, 5, 0), RetrievalOptions('hybrid', 20, 5, 0),
                    RetrievalOptions('hybrid_rerank', 20, 5, best['threshold']), RetrievalOptions('dense', 20, 1, 0)]
    common = {'created_at': datetime.now(timezone.utc).isoformat(), 'mode': 'openai', 'examples': len(examples),
              'chat_model': config.CHAT_MODEL, 'embedding_model': config.EMBEDDING_MODEL, 'dataset_sha256': dataset_hash,
              'corpus_sha256': corpus_hash, 'corpus': list_documents(), 'shared_embedding_batch_seconds': cache['embedding_batch_seconds'],
              'embedding_note': 'Same real query vectors reused for all configurations. Reported per-row latency excludes this shared batch and optional judge time.',
              'calibration_note': 'Threshold tuned on these same 16 labeled examples, including expected evidence. Results are in-sample and need held-out validation.'}
    comparison = {'conditions': common, 'threshold_trials': trials, 'selected_threshold': best['threshold'], 'retrieval': {}, 'answers': {}}
    for options in options_list:
        name = 'dense_top1_control' if options.top_k == 1 else options.mode
        rows = retrieval_run(examples, vectors, options)
        report = {**common, 'top_k': options.top_k, 'retrieval_configuration': asdict(options), 'evaluation_kind': 'retrieval_only',
                  'summary': average(rows, ['source_recall_at_k', 'source_precision_at_k', 'mrr', 'expected_evidence_coverage', 'retrieval_seconds', 'selected_count']), 'results': rows}
        archive_run(report, f'Retrieval: {name}')
        (output / f'retrieval-{name}.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        comparison['retrieval'][name] = report['summary']
        print(f'Retrieval {name}: {json.dumps(report["summary"])}', flush=True)
        if not answers or options.top_k == 1:
            continue
        rows = []
        for index, (example, vector) in enumerate(zip(examples, vectors)):
            metric = Trace()
            token = active_trace.set(metric)
            try:
                started = time.perf_counter()
                answer = answer_question(example['question'], client=client, retrieval_options=options, query_embedding=vector)
                latency = time.perf_counter()-started
                row = {'question': example['question'], 'reference_answer': example['reference_answer'], 'answer': answer.answer, 'raw_answer': answer.raw_answer,
                       'sources': [c.filename for c in answer.citations], 'citations': [c.model_dump() for c in answer.citations],
                       'retrieved_chunks': [c.model_dump() for c in answer.retrieved_chunks], 'diagnostics': answer.diagnostics,
                       'source_recall_at_k': source_recall(answer.retrieved_sources, example['expected_sources']),
                       'source_precision_at_k': source_precision(answer.retrieved_sources, example['expected_sources']),
                       'mrr': reciprocal_rank(answer.retrieved_sources, example['expected_sources']),
                       'answer_lexical_f1': lexical_f1(answer.answer, example['reference_answer']),
                       'faithfulness_lexical_proxy': evidence_coverage(answer.answer, [c.snippet for c in answer.retrieved_chunks]),
                       'citation_support_lexical_proxy': support_accuracy(answer.citations, example.get('expected_evidence', '')),
                       'citation_validity': citation_validity(answer.raw_answer or answer.answer, [c.marker for c in answer.retrieved_chunks]),
                       'latency_seconds': latency}
                if judge:
                    row.update(judge_quality(client, example['question'], answer.answer, example['reference_answer'], answer.citations))
                row['telemetry'] = metric.snapshot()
                rows.append(row)
            finally:
                active_trace.reset(token)
            # Paid work survives a later failure; no silent skips or fabricated zeros.
            (output / f'answers-{name}.partial.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
            print(f'Answers {name}: {index+1}/{len(examples)}', flush=True)
        keys = ['source_recall_at_k', 'source_precision_at_k', 'mrr', 'answer_lexical_f1', 'faithfulness_lexical_proxy', 'citation_support_lexical_proxy', 'citation_validity', 'latency_seconds']
        if judge:
            keys += ['answer_correctness_judge', 'faithfulness_judge', 'citation_support_judge']
        report = {**common, 'top_k': options.top_k, 'retrieval_configuration': asdict(options), 'evaluation_kind': 'answers', 'judge_enabled': judge,
                  'judge_missing_counts': {key: sum(row.get(key) is None for row in rows) for key in keys if key.endswith('_judge')},
                  'summary': average(rows, keys), 'results': rows}
        archive_run(report, f'Answers: {name}')
        (output / f'answers-{name}.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        comparison['answers'][name] = report['summary']
    final_corpus = collection().get(include=['documents', 'metadatas'])
    assert fingerprint(sorted(zip(final_corpus['ids'], final_corpus['documents'], final_corpus['metadatas']))) == corpus_hash, 'Corpus changed during ablation'
    (output / 'comparison.json').write_text(json.dumps(comparison, indent=2), encoding='utf-8')
    return comparison

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, default=Path('evals/sample.jsonl'))
    parser.add_argument('--output', type=Path, default=config.BASE_DIR / 'evals' / 'ablations' / str(uuid4()))
    parser.add_argument('--answers', action='store_true')
    parser.add_argument('--judge', action='store_true')
    args = parser.parse_args()
    execute(args.dataset, args.output, args.answers, args.judge)
