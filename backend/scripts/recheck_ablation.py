"""Recheck one recorded regression without regenerating unaffected answers."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.eval.ablation import average, fingerprint
from app import config
from app.eval.history import archive_run
from app.eval.metrics import lexical_f1, citation_validity, support_accuracy, evidence_coverage, source_recall, source_precision, reciprocal_rank
from app.eval.run import judge_quality
from app.observability import Trace, active_trace
from app.provider import get_client, demo_enabled
from app.rag import answer_question
from app.retrieval import RetrievalOptions

def recheck(source:Path, output:Path, question:str):
    if demo_enabled() or output.exists():
        raise ValueError('Requires real mode and a new output path')
    report=json.loads(source.read_text(encoding='utf-8'))
    options=RetrievalOptions(**report['retrieval_configuration'])
    dataset=[json.loads(line) for line in Path('evals/sample.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    example=next(e for e in dataset if e['question']==question)
    index=next(i for i,row in enumerate(report['results']) if row['question']==question)
    client=get_client(); trace=Trace(); token=active_trace.set(trace)
    try:
        # Reuse the same real query embedding as the original ablation.
        caches=list(Path('data').glob('query-vectors-*.json'))
        expected_key=fingerprint({'questions':[e['question'] for e in dataset],'model':config.EMBEDDING_MODEL})
        cache=next(json.loads(p.read_text()) for p in caches if json.loads(p.read_text())['key']==expected_key)
        vector=cache['vectors'][next(i for i,e in enumerate(dataset) if e['question']==question)]
        started=time.perf_counter()
        answer=answer_question(question,client=client,retrieval_options=options,query_embedding=vector)
        latency=time.perf_counter()-started
        row={'question':question,'reference_answer':example['reference_answer'],'answer':answer.answer,'raw_answer':answer.raw_answer,
             'sources':[c.filename for c in answer.citations],'citations':[c.model_dump() for c in answer.citations],
             'retrieved_chunks':[c.model_dump() for c in answer.retrieved_chunks],'diagnostics':answer.diagnostics,
             'source_recall_at_k':source_recall(answer.retrieved_sources,example['expected_sources']),
             'source_precision_at_k':source_precision(answer.retrieved_sources,example['expected_sources']),
             'mrr':reciprocal_rank(answer.retrieved_sources,example['expected_sources']),
             'answer_lexical_f1':lexical_f1(answer.answer,example['reference_answer']),
             'faithfulness_lexical_proxy':evidence_coverage(answer.answer,[c.snippet for c in answer.retrieved_chunks]),
             'citation_support_lexical_proxy':support_accuracy(answer.citations,example['expected_evidence']),
             'citation_validity':citation_validity(answer.raw_answer or answer.answer,[c.marker for c in answer.retrieved_chunks]),
             'latency_seconds':latency,**judge_quality(client,question,answer.answer,example['reference_answer'],answer.citations),
             'telemetry':trace.snapshot()}
    finally:
        active_trace.reset(token)
    report['results'][index]=row
    report['summary']=average(report['results'],list(report['summary']))
    report['judge_missing_counts']={key:sum(r.get(key) is None for r in report['results']) for key in report['judge_missing_counts']}
    report['updated_at']=datetime.now(timezone.utc).isoformat()
    report['rechecks']=[{'question':question,'reason':'Preserve a valid cited partial answer after introductory uncertainty','original_report':str(source)}]
    archive_run(report,'Answers: hybrid_rerank (validated partial answers)')
    output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'answer':row['answer'],'summary':report['summary']},indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--question',default='Does this project isolate multiple user accounts?')
    args=parser.parse_args();recheck(args.source,args.output,args.question)
