from app.retrieval import BM25, reciprocal_rank_fusion, retrieve, RetrievalOptions
from app.provider import DemoClient
from app.store import save_document, delete_document
from app.rag import answer_question
from app import config
import pytest

def index(doc_id, filename, text):
    vector = DemoClient().embed(input=[text]).data[0].embedding
    save_document(doc_id, filename, [text], [1], [vector])

def test_bm25_idf_length_normalization():
    bm25 = BM25(['orchid orchid code', 'orchid code '+'filler '*50, 'unrelated sentence'])
    scores = bm25.scores('orchid code')
    assert scores[0] > scores[1] > scores[2] == 0
    assert bm25.scores('the is what') == [0,0,0]

def test_rrf_and_duplicate_handling():
    scores = reciprocal_rank_fusion([['a','b','a'],['b','c']])
    assert scores['b'] > scores['a'] > scores['c']
    assert scores['a'] == 1/61

@pytest.mark.parametrize('mode',['dense','hybrid','hybrid_rerank'])
def test_retrieval_diagnostics_and_citations(mode):
    index('one','guide.txt','The support escalation code is ORCHID-42.')
    index('two','distractor.txt','Carrots grow in soil.')
    client=DemoClient()
    response=answer_question('What is the support escalation code?',client=client,retrieval_options=RetrievalOptions(mode,10,5,.3))
    assert 'ORCHID-42' in response.answer
    assert response.citations[0].filename == 'guide.txt'
    assert response.diagnostics and all('text' not in row for row in response.diagnostics)
    assert response.telemetry['selected_count'] == len(response.retrieved_chunks)
    assert response.telemetry['stages_seconds']['retrieval'] >= 0
    if mode == 'hybrid_rerank':
        assert len(response.retrieved_chunks) == 1
        assert all(row['rerank_score'] is not None for row in response.diagnostics)

def test_empty_and_filtered_queries_skip_generation():
    vector=DemoClient().embed(input=['unknown words']).data[0].embedding
    assert retrieve('unknown words',vector,RetrievalOptions('hybrid_rerank',5,5,.9))[0] == []
    index('one','x.txt','Bananas are yellow.')
    response=answer_question('unknown words',retrieval_options=RetrievalOptions('hybrid_rerank',5,5,.99))
    assert response.citations == [] and 'generation' not in response.telemetry['stages_seconds']

def test_keyword_snapshot_invalidates_after_deletion_and_insert():
    index('one','x.txt','The escalation code is ORCHID.')
    vector=DemoClient().embed(input=['escalation code']).data[0].embedding
    retrieve('escalation code',vector,RetrievalOptions('hybrid',10,5,0))
    delete_document('one')
    index('two','y.txt','The escalation code is VIOLET.')
    selected, _, _=retrieve('escalation code',vector,RetrievalOptions('hybrid',10,5,0))
    assert [c.chunk_id for c in selected] == ['two:0']

def test_optional_model_fallback(monkeypatch):
    index('one','guide.txt','The upload limit is 20 MB.')
    monkeypatch.setattr(config,'RERANKER','cross_encoder')
    monkeypatch.setattr(config,'RERANKER_MODEL','')
    vector=DemoClient().embed(input=['upload limit']).data[0].embedding
    _,_,info=retrieve('upload limit',vector,RetrievalOptions('hybrid_rerank',5,5,0))
    assert info['reranker_used']=='lightweight' and info['fallback']

def test_keyword_memory_bound(monkeypatch):
    index('one','guide.txt','The upload limit is 20 MB.')
    monkeypatch.setattr(config,'MAX_KEYWORD_CHUNKS',0)
    vector=DemoClient().embed(input=['upload limit']).data[0].embedding
    selected,_,info=retrieve('upload limit',vector,RetrievalOptions('hybrid',5,5,0))
    assert selected and 'memory bound' in info['fallback']

def test_invalid_options():
    with pytest.raises(ValueError): RetrievalOptions('invalid')
    with pytest.raises(ValueError): RetrievalOptions(threshold=float('nan'))

def test_keyword_only_candidate_gets_a_real_cosine_score(monkeypatch):
    from app import retrieval
    from app.store import collection
    index('noise','noise.txt','Carrots grow in soil.')
    index('fact','guide.txt','The escalation code is ORCHID.')
    col=collection()
    stored=col.get(ids=['noise:0'],include=['documents','metadatas'])
    monkeypatch.setattr(col,'query',lambda **kwargs:{'ids':[['noise:0']],'documents':[stored['documents']],'metadatas':[stored['metadatas']],'distances':[[.9]]})
    monkeypatch.setattr(retrieval,'collection',lambda:col)
    vector=DemoClient().embed(input=['escalation code']).data[0].embedding
    selected,candidates,_=retrieve('escalation code',vector,RetrievalOptions('hybrid',1,1,0))
    keyword=next(c for c in candidates if c.chunk_id=='fact:0')
    assert keyword.keyword_score>0 and keyword.vector_similarity>0
    assert selected[0].chunk_id=='fact:0'
