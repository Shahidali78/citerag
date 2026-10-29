import json
from pathlib import Path
from unittest.mock import Mock
import pytest
from app import config
from app.eval.independent_data import source_catalog,build_rows,HELDOUT,FINAL,validate_rows,fingerprint
from app.eval.heldout import verify_protocol,retrieval_metrics,deterministic_metrics,REFUSAL,judge,summarize
from app.observability import Trace
from types import SimpleNamespace

ROOT=config.BASE_DIR/'evals/heldout'

def test_heldout_and_reserved_sources_are_independently_verifiable():
    held=build_rows(HELDOUT,'held_out');final=build_rows(FINAL,'final_test')
    old={json.loads(line)['question'] for line in (config.BASE_DIR/'evals/sample.jsonl').read_text().splitlines()}
    validate_rows(held+final,source_catalog(),old)
    assert len(held)==40 and len(final)==12
    assert sum(not row['answerable'] for row in held)==8
    assert len({row['category'] for row in held})==7
    for row in held:
        if row['category']=='multi_chunk':
            assert not set.intersection(*(set(e['acceptable_chunk_ids']) for e in row['evidence']))

def test_protocol_freezes_settings_and_reserves_final_set():
    rows,protocol,split=verify_protocol(ROOT/'heldout_v1.jsonl',ROOT/'protocol.json')
    assert len(rows)==40 and split=='held_out'
    assert protocol['configurations'][-1]['threshold']==.2
    with pytest.raises(ValueError,match='Final test is reserved'):
        verify_protocol(ROOT/'final_test_v1.jsonl',ROOT/'protocol.json')

def test_duplicate_overlapping_evidence_is_an_any_of_group():
    example={'answerable':True,'expected_sources':['a'],'expected_evidence':'fact','evidence':[{'acceptable_chunk_ids':['a:0','a:1']},{'acceptable_chunk_ids':['b:0']}]}
    chunks=[{'filename':'a','chunk_id':'a:1','snippet':'fact'},{'filename':'b','chunk_id':'b:0','snippet':'other'}]
    result=retrieval_metrics(example,chunks)
    assert result['evidence_recall_at_k']==1 and result['evidence_precision_at_k']==1
    assert retrieval_metrics({'answerable':False},[])['source_recall_at_k'] is None

def test_unanswerable_refusal_is_not_scored_as_citation_failure():
    row={'answerable':False,'expected_sources':[],'evidence':[]}
    response={'answer':REFUSAL,'raw_answer':'The documents do not say.','citations':[],'retrieved_chunks':[]}
    scores=deterministic_metrics(row,response)
    assert scores['strict_abstention']==1
    assert scores['citation_validity'] is None and scores['answer_lexical_f1'] is None
    assert scores['mrr'] is None

def test_no_citations_on_answerable_question_still_gets_coverage_penalty():
    row={'answerable':True,'expected_sources':['a'],'evidence':[{'acceptable_chunk_ids':['a:0']}],'expected_evidence':'fact','reference_answer':'fact'}
    scores=deterministic_metrics(row,{'answer':REFUSAL,'citations':[],'retrieved_chunks':[]})
    assert scores['answerable_citation_coverage']==0 and scores['false_abstention']==1

def test_heldout_judge_keeps_invalid_values_unknown():
    client=Mock();client.responses.create.return_value=SimpleNamespace(output_text='{"answer_correctness_judge":0.5,"faithfulness_judge":true,"citation_support_judge":2}')
    scores=judge(client,{'question':'q','answerable':False,'reference_answer':'r','evidence':[]},{'answer':'a','citations':[],'retrieved_chunks':[]},Trace())
    assert scores=={'answer_correctness_judge':.5,'faithfulness_judge':None,'citation_support_judge':None}
    assert client.responses.create.call_args.kwargs['text']['format']['strict'] is True

def test_completed_checkpoint_cannot_repeat_paid_work(tmp_path,monkeypatch):
    from app.eval import heldout
    from app.provider import DemoClient
    from app.store import save_document,collection
    monkeypatch.setenv('CITERAG_DEMO','false')
    client=DemoClient()
    text='The support escalation code is ORCHID.'
    save_document('doc','a.txt',[text],[1],[client.embed(input=[text]).data[0].embedding])
    example={'id':'ho-test','split':'held_out','category':'direct_fact','question':'What is the support escalation code?','answerable':True,'reference_answer':'ORCHID','expected_sources':['a.txt'],'expected_evidence':text,'evidence':[{'acceptable_chunk_ids':['doc:0']} ]}
    corpus=[{'chunk_id':'doc:0','text':text,'filename':'a.txt','page':1}]
    protocol={'corpus_sha256':fingerprint(corpus),'prompt_sha256':'test','configurations':[{'mode':'dense','candidates':5,'top_k':5,'threshold':0}]}
    monkeypatch.setattr(heldout,'verify_protocol',lambda *args:([example],protocol,'held_out'))
    factory=Mock(return_value=client);monkeypatch.setattr(heldout,'get_client',factory)
    monkeypatch.setattr(heldout,'judge',lambda *args:dict.fromkeys(heldout.JUDGES,1.0))
    output=tmp_path/'run'
    result=heldout.run(Path('unused'),Path('unused'),output)
    assert result['configurations']['dense']['summary']['source_recall_at_k']==1
    with pytest.raises(ValueError,match='Completed reports are immutable'):
        heldout.run(Path('unused'),Path('unused'),output,resume=True)
    assert factory.call_count==1

def test_judge_failure_resume_reuses_paid_generation(tmp_path,monkeypatch):
    from app.eval import heldout
    from app.provider import DemoClient
    from app.store import save_document
    monkeypatch.setenv('CITERAG_DEMO','false')
    client=DemoClient();text='The support escalation code is ORCHID.'
    save_document('doc','a.txt',[text],[1],[client.embed(input=[text]).data[0].embedding])
    example={'id':'ho-resume','split':'held_out','category':'direct_fact','question':'What is the support escalation code?','answerable':True,'reference_answer':'ORCHID','expected_sources':['a.txt'],'expected_evidence':text,'evidence':[{'acceptable_chunk_ids':['doc:0']}]}
    corpus=[{'chunk_id':'doc:0','text':text,'filename':'a.txt','page':1}]
    protocol={'corpus_sha256':fingerprint(corpus),'prompt_sha256':'test','configurations':[{'mode':'dense','candidates':5,'top_k':5,'threshold':0}]}
    monkeypatch.setattr(heldout,'verify_protocol',lambda *args:([example],protocol,'held_out'))
    monkeypatch.setattr(heldout,'get_client',lambda:client)
    generate=Mock(wraps=heldout.answer_question);monkeypatch.setattr(heldout,'answer_question',generate)
    grader=Mock(side_effect=RuntimeError('simulated provider failure'));monkeypatch.setattr(heldout,'judge',grader)
    output=tmp_path/'run'
    with pytest.raises(RuntimeError):heldout.run(Path('unused'),Path('unused'),output)
    grader.side_effect=None;grader.return_value=dict.fromkeys(heldout.JUDGES,1.0)
    heldout.run(Path('unused'),Path('unused'),output,resume=True)
    assert generate.call_count==1 and grader.call_count==2
    report=json.loads((output/'answers-dense.json').read_text())
    assert report['results'][0]['generation_reused_on_resume'] is True
