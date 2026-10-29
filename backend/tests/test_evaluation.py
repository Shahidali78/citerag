import json
from pathlib import Path
from app.eval.metrics import source_precision, reciprocal_rank, evidence_coverage, lexical_f1, citation_validity
from app.eval.run import run
from app.provider import DemoClient
from app.store import save_document
from app.eval.run import judge_quality
from types import SimpleNamespace
from unittest.mock import Mock

def test_rank_metrics():
    assert source_precision(['b','a','a'],['a']) == 0.6667
    assert reciprocal_rank(['b','a'],['a']) == 0.5
    assert reciprocal_rank([],['a']) == 0
    assert evidence_coverage('cat dog',['cat']) == 0.5
    assert lexical_f1('20 MB [1]', '20 MB') == 1.0
    assert citation_validity('A claim [01]', ['[1]']) == 1.0

def test_saved_evaluation(tmp_path):
    text='CiteRAG accepts PDF, Markdown, and plain text files.'
    save_document('doc','sample.md',[text],[1],[DemoClient().embed(input=[text]).data[0].embedding])
    report=run(Path('evals/sample.jsonl'),tmp_path/'results.json')
    assert report['examples'] >= 15
    assert report['mode'] == 'demo'
    assert json.loads((tmp_path/'results.json').read_text()) == report
    assert all(row['latency_seconds'] >= 0 for row in report['results'])

def test_judge_scores_and_failures():
    client=Mock()
    client.responses.create.return_value=SimpleNamespace(output_text='{"answer_correctness_judge": 0.8, "faithfulness_judge": 2, "citation_support_judge": true}')
    result=judge_quality(client,'question','answer','reference',[])
    assert result == {'answer_correctness_judge':0.8,'faithfulness_judge':None,'citation_support_judge':None}
    client.responses.create.return_value=SimpleNamespace(output_text='malformed')
    assert all(score is None for score in judge_quality(client,'q','a','r',[]).values())
    client.responses.create.return_value=SimpleNamespace(output_text='null')
    assert all(score is None for score in judge_quality(client,'q','a','r',[]).values())

def test_retry_only_missing_judgments(tmp_path, monkeypatch):
    from app.eval import run as runner
    from app import config
    monkeypatch.setenv('CITERAG_DEMO', 'false')
    complete = dict.fromkeys(runner.JUDGE_KEYS, 0.8)
    incomplete = {key: None for key in runner.JUDGE_KEYS}
    report = {'mode': 'openai', 'judge_enabled': True, 'chat_model': config.CHAT_MODEL,
              'summary': complete, 'results': [
                  {'question': 'q1', 'answer': 'a', 'reference_answer': 'r', 'citations': [], **complete},
                  {'question': 'q2', 'answer': 'a', 'reference_answer': 'r', 'citations': [], **incomplete}]}
    output = tmp_path / 'results.json'
    output.write_text(json.dumps(report))
    monkeypatch.setattr(runner, 'get_client', Mock())
    judge = Mock(return_value=dict.fromkeys(runner.JUDGE_KEYS, 1.0))
    monkeypatch.setattr(runner, 'judge_quality', judge)
    result = runner.retry_missing_judges(output)
    assert judge.call_count == 1
    assert result['results'][0]['answer_correctness_judge'] == 0.8
    assert result['summary']['answer_correctness_judge'] == 0.9
    runner.retry_missing_judges(output)
    assert judge.call_count == 1
