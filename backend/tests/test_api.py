from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from app.main import app
from app import config, main
from app.provider import DemoClient
from app.rag import answer_question
from app.store import save_document, collection

@pytest.fixture
def api():
    with TestClient(app) as client:
        yield client

@pytest.mark.parametrize('filename,data,status', [('bad.exe',b'abc',415), ('empty.txt',b'  ',422), ('bad.pdf',b'invalid',422), ('bad.txt',b'\xff',422)])
def test_invalid_upload(api, filename, data, status):
    assert api.post('/documents', files={'file':(filename,data)}).status_code == status

def test_upload_limit(api, monkeypatch):
    monkeypatch.setattr(config, 'MAX_UPLOAD_BYTES', 3)
    assert api.post('/documents', files={'file':('big.txt',b'four')}).status_code == 413

def test_ingest_chat_delete(api):
    r = api.post('/documents', files={'file':('guide.md',b'The maximum upload size is 20 MB per file.')})
    assert r.status_code == 201
    document = r.json()
    assert document['chunks'] == 1
    assert len(api.get('/documents').json()) == 1
    answer = api.post('/chat', json={'question':'What is the maximum upload size?', 'top_k':3}).json()
    assert answer['citations'][0]['chunk_id'] == f"{document['id']}:0"
    assert answer['citations'][0]['page'] == 1
    assert '20 MB' in answer['answer']
    assert api.delete(f"/documents/{document['id']}").status_code == 200
    assert collection().count() == 0
    assert api.get('/documents').json() == []
    assert api.delete(f"/documents/{document['id']}").status_code == 404

def test_empty_database_needs_no_key(api, monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.delenv('CITERAG_DEMO', raising=False)
    result = api.post('/chat', json={'question':'Anything?'}).json()
    assert result['retrieved_count'] == 0 and result['citations'] == []

@pytest.mark.parametrize('payload', [{'question':'  '}, {'question':'q','top_k':0}, {'question':'q','top_k':13}, {'question':'x'*4001}])
def test_request_validation(api,payload):
    assert api.post('/chat',json=payload).status_code == 422

def test_missing_credentials(api,monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.delenv('CITERAG_DEMO', raising=False)
    assert api.post('/documents',files={'file':('a.txt',b'Valid text')}).status_code == 503

def test_embedding_error_is_redacted(api,monkeypatch):
    client = Mock()
    client.embeddings.create.side_effect = RuntimeError('secret-token')
    monkeypatch.setattr(main,'get_client',lambda:client)
    r=api.post('/documents',files={'file':('a.txt',b'Text')})
    assert r.status_code == 502 and 'secret-token' not in r.text

def test_pdf_pages(api,monkeypatch):
    reader = SimpleNamespace(pages=[SimpleNamespace(extract_text=lambda:'First page'),SimpleNamespace(extract_text=lambda:'Second page')])
    monkeypatch.setattr(main,'PdfReader',lambda _:reader)
    assert api.post('/documents',files={'file':('a.pdf',b'mocked')}).status_code == 201
    assert sorted(m['page'] for m in collection().get()['metadatas']) == [1,2]

def test_real_blank_pdf(api):
    writer=PdfWriter(); writer.add_blank_page(width=72,height=72)
    buffer=BytesIO(); writer.write(buffer)
    assert api.post('/documents',files={'file':('blank.pdf',buffer.getvalue())}).status_code == 422

@pytest.mark.parametrize('output,expected', [('A supported claim [1] and fake [99]',1),('A supported claim [01]',1),('When evidence is insufficient, the assistant reports that the documents do not provide enough information [1].',1),('Uncited claim',0),('The documents do not provide enough information. [1]',0)])
def test_citation_validation(output, expected):
    client=DemoClient()
    save_document('doc','a.txt',['A supported claim'],[2],[client.embed(input=['A supported claim']).data[0].embedding])
    client.responses.create=Mock(return_value=SimpleNamespace(output_text=output))
    answer=answer_question('supported claim',client=client)
    assert len(answer.citations) == expected and '[99]' not in answer.answer
    assert answer.raw_answer == output
    if expected:
        assert answer.citations[0].chunk_id == 'doc:0'
        assert '[1]' in answer.answer
    else:
        assert 'enough information' in answer.answer

def test_cors_and_reports(api):
    r=api.options('/chat',headers={'Origin':'http://localhost:3000','Access-Control-Request-Method':'POST'})
    assert r.headers['access-control-allow-origin'] == 'http://localhost:3000'
    assert api.get('/evaluations').json()['available'] is False
    config.EVALUATION_PATH.write_text('{"examples": 1, "summary": {}, "results": []}')
    assert api.get('/evaluations').json()['examples'] == 1
    config.EVALUATION_PATH.write_text('broken')
    assert api.get('/evaluations').status_code == 500

def test_embedding_count_validation():
    with pytest.raises(ValueError):
        save_document('doc','x.txt',['text'],[1],[])

def test_mock_openai_embeddings_and_order(api, monkeypatch):
    monkeypatch.setenv('CITERAG_DEMO', 'false')
    monkeypatch.setenv('OPENAI_API_KEY', 'unit-test-placeholder')
    client = Mock()
    client.embeddings.create.return_value = SimpleNamespace(data=[SimpleNamespace(index=1,embedding=[0.0,1.0]),SimpleNamespace(index=0,embedding=[1.0,0.0])])
    monkeypatch.setattr(main, 'get_client', lambda: client)
    r=api.post('/documents',files={'file':('two.txt',b'alpha '*200)})
    assert r.status_code == 201
    chunks=collection().get(include=['embeddings'])
    assert chunks['embeddings'][chunks['ids'].index(r.json()['id']+':0')].tolist() == [1.0,0.0]
    assert client.embeddings.create.call_args.kwargs['model'] == config.EMBEDDING_MODEL

def test_unsupported_question_has_no_citations(api):
    api.post('/documents',files={'file':('a.txt',b'The maximum upload size is 20 MB.')})
    result=api.post('/chat',json={'question':'Who won the galactic chess tournament?'}).json()
    assert result['citations'] == [] and 'enough information' in result['answer']
