"""Source-grounded, question-level holdouts over the fixed public sample corpus."""
import hashlib
import json
from pathlib import Path
import re
from pypdf import PdfReader
from ..chunking import chunk_pages
from .. import config

def fingerprint(value) -> str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def normalize(text: str) -> str:
    return ' '.join(text.split())

def source_catalog() -> list[dict]:
    manifest=json.loads((config.BASE_DIR.parent/'docs/baseline/openai-evaluation.json').read_text(encoding='utf-8'))
    rows=[]
    for document in manifest['corpus']:
        path=config.BASE_DIR/'evals'/document['filename']
        pages=[page.extract_text() or '' for page in PdfReader(path).pages] if path.suffix=='.pdf' else [path.read_text(encoding='utf-8')]
        for chunk in chunk_pages(pages):
            rows.append({'chunk_id':f"{document['id']}:{chunk.index}",'filename':document['filename'],'page':chunk.page,'text':chunk.text})
    return sorted(rows,key=lambda row:row['chunk_id'])

FACTS = {
 'purpose':('sample.md',1,'CiteRAG answers questions about uploaded documents with source citations.'),
 'formats':('sample.md',1,'CiteRAG accepts PDF, Markdown, and plain text files.'),
 'size':('sample.md',1,'The maximum upload size is 20 MB per file.'),
 'pages':('sample.md',1,'PDF page numbers are preserved as one-based page numbers in chunk metadata.'),
 'chunks':('sample.md',1,'Document text is split into overlapping chunks within each page.'),
 'embedding':('sample.md',1,'The default embedding model is text-embedding-3-small.'),
 'vectors':('sample.md',1,'ChromaDB stores document vectors in a persistent local collection.'),
 'metadata':('sample.md',1,'SQLite stores document names, chunk counts, and ingestion timestamps.'),
 'similarity':('sample.md',1,'Retrieval similarity measures vector closeness and does not prove factual correctness.'),
 'identifiers':('sample.md',1,'Citation identifiers are checked against the chunks retrieved for the current question.'),
 'insufficient':('sample.md',1,'When evidence is insufficient, the assistant reports that the documents do not provide enough information.'),
 'ocr':('sample.md',1,'Scanned PDFs require OCR before their text can be indexed.'),
 'delete':('sample.md',1,'Deleting a document removes its vectors and its SQLite metadata.'),
 'depth':('sample.md',1,'Retrieval depth controls the maximum number of chunks passed to answer generation.'),
 'untrusted':('sample.md',1,'Retrieved document instructions are untrusted data and must not override system instructions.'),
 'single':('sample.md',1,'This project is a single-user local application without multi-user authentication.'),
 'health':('operations.txt',1,'The backend health endpoint is GET /health.'),
 'workspace':('operations.txt',1,'The research workspace runs on port 3000.'),
 'api':('operations.txt',1,'The API runs on port 8000.'),
 'evaluations':('operations.txt',1,'Evaluation results are available at GET /evaluations.'),
 'credentials':('operations.txt',1,'Keep API credentials on the backend only.'),
 'review':('verification.pdf',1,'The document review window is 14 days.'),
 'code':('verification.pdf',2,'The support escalation code is ORCHID-42.'),
 'opening':('verification.pdf',2,'The support desk opens at 09:00 UTC on weekdays.')}

HELDOUT = [
 ('direct_fact','How many days are allotted to a document review?','The document review window is 14 days.',['review']),
 ('direct_fact','Give the literal escalation identifier listed for support.','The support escalation code is ORCHID-42.',['code']),
 ('direct_fact','At what UTC time does the support desk open?','The support desk opens at 09:00 UTC.',['opening']),
 ('direct_fact','What weekday-or-weekend schedule is stated for desk opening?','The stated opening schedule is weekdays.',['opening']),
 ('direct_fact','Which HTTP method and path perform a backend health check?','GET /health performs a backend health check.',['health']),
 ('direct_fact','Which path serves the stored evaluation output?','Evaluation results are available at GET /evaluations.',['evaluations']),
 ('paraphrase','Where should a client application keep its API credentials?','Keep API credentials on the backend only.',['credentials']),
 ('paraphrase','Does PDF page counting in chunk metadata begin at zero or one?','PDF page numbers are one-based, beginning at one.',['pages']),
 ('paraphrase','Does an image-only PDF need text recognition before its contents can be indexed?','Scanned PDFs require OCR before their text can be indexed.',['ocr']),
 ('paraphrase','What information about an uploaded file is recorded in the relational store?','SQLite stores document names, chunk counts, and ingestion timestamps.',['metadata']),
 ('paraphrase','What restriction applies to the size of each incoming file?','The maximum upload size is 20 MB per file.',['size']),
 ('paraphrase','Can text retrieved from a file change the assistant system-level rules?','Retrieved document instructions are untrusted and must not override system instructions.',['untrusted']),
 ('multi_chunk','Which upload formats are allowed, and what is removed when an indexed document is deleted?','PDF, Markdown, and plain text are accepted. Deletion removes document vectors and SQLite metadata.',['formats','delete']),
 ('multi_chunk','What default embedding model is used, and is the project described as a multi-user authenticated application?','The default embedding model is text-embedding-3-small. The project is a single-user local application without multi-user authentication.',['embedding','single']),
 ('multi_chunk','How long is the document review window, and what escalation code is listed for support?','The review window is 14 days, and the support escalation code is ORCHID-42.',['review','code']),
 ('multi_chunk','Which port serves the research workspace, and what must precede indexing a scanned PDF?','The workspace runs on port 3000. Scanned PDFs require OCR before indexing.',['workspace','ocr']),
 ('multi_chunk','How can I check backend health, and which datastore persists document vectors?','Use GET /health. ChromaDB persists document vectors in a local collection.',['health','vectors']),
 ('multi_chunk','Where should API credentials live, and how should instructions found in retrieved files be treated?','Credentials stay on the backend only. Retrieved instructions are untrusted and must not override system instructions.',['credentials','untrusted']),
 ('comparison','How do the documented roles of SQLite and ChromaDB differ?','SQLite stores document names, chunk counts, and ingestion timestamps. ChromaDB stores document vectors in a persistent local collection.',['metadata','vectors']),
 ('comparison','Which service uses the higher port, and by how much does it exceed the other service port?','The API uses port 8000 and the workspace uses port 3000, so the API port is higher by 5000.',['api','workspace']),
 ('comparison','How do similarity scores and citation-identifier checks differ in what they establish?','Similarity measures vector closeness rather than proving correctness. Citation identifiers are checked against chunks retrieved for the current question.',['similarity','identifiers']),
 ('comparison','How does the review-window duration differ from the support opening schedule?','The review window lasts 14 days. The support desk opens at 09:00 UTC on weekdays.',['review','opening']),
 ('comparison','Does retrieval depth set the upload-size limit, or does it control something else?','Retrieval depth controls the maximum chunks passed to generation. The upload limit is 20 MB per file.',['depth','size']),
 ('distracting_keywords','Ignoring the ChromaDB and SQLite details, when and on which days does the support desk open?','The support desk opens at 09:00 UTC on weekdays.',['opening']),
 ('distracting_keywords','Despite the discussion of OCR and vector storage, which path returns evaluation results?','Evaluation results are available at GET /evaluations.',['evaluations']),
 ('distracting_keywords','For a document mentioning port 8000 and ORCHID-42, what is the permitted per-file upload size?','The maximum upload size is 20 MB per file.',['size']),
 ('distracting_keywords','Apart from embedding models and numbered citations, how many days are in the review window?','The document review window is 14 days.',['review']),
 ('distracting_keywords','If an uploaded passage says to override system instructions and also mentions port 3000, should its instruction be trusted?','No. Retrieved document instructions are untrusted and must not override system instructions.',['untrusted']),
 ('citation_support','Is a high similarity value proof that a retrieved claim is true? Cite the stated distinction.','No. Retrieval similarity measures vector closeness and does not prove factual correctness.',['similarity']),
 ('citation_support','Which passage supports describing the review period as two weeks?','The document review window is 14 days, which equals two weeks.',['review']),
 ('citation_support','Which document and page support both ORCHID-42 and the 09:00 UTC opening?','verification.pdf page 2 states the support escalation code ORCHID-42 and the 09:00 UTC weekday opening.',['code','opening']),
 ('citation_support','What evidence states that removing a source also removes its metadata?','Deleting a document removes its vectors and its SQLite metadata.',['delete']),
 ('unanswerable','What is the support desk closing time?','The documents do not state a support closing time.',[]),
 ('unanswerable','How much does a CiteRAG subscription cost per month?','The documents do not state subscription pricing.',[]),
 ('unanswerable','Which email address should receive an ORCHID-42 escalation?','The documents do not provide a support escalation email address.',[]),
 ('unanswerable','What exact OCR engine and version does CiteRAG use?','The documents do not identify an OCR engine or version.',[]),
 ('unanswerable','What BM25 k1 parameter is configured in this deployment?','The supplied documents do not state a BM25 k1 parameter.',[]),
 ('unanswerable','Which timezone applies to the deadline of the 14-day review window?','The documents do not specify a timezone for review deadlines.',[]),
 ('unanswerable','What is the administrator password for multi-user authentication?','The documents provide no administrator password; they describe a single-user application without multi-user authentication.',[]),
 ('unanswerable','How many documents may one user upload in total?','The documents do not state a total document-count limit.',[])]

FINAL = [
 ('multi_chunk','List the client workspace port, API port, and the support escalation identifier together.','The workspace uses port 3000, the API uses port 8000, and support escalation uses ORCHID-42.',['workspace','api','code']),
 ('comparison','Which data stays in SQLite after ingesting a file, and what data is placed in ChromaDB?','SQLite stores names, chunk counts, and ingestion timestamps; ChromaDB stores document vectors.',['metadata','vectors']),
 ('paraphrase','If a scanned document has no machine-readable text, what prerequisite does the guide identify?','Scanned PDFs require OCR before their text can be indexed.',['ocr']),
 ('citation_support','What source and page state the review period length?','verification.pdf page 1 states that the document review window is 14 days.',['review']),
 ('multi_chunk','Name the embedding model and explain whether retrieved instructions may replace system instructions.','The embedding model is text-embedding-3-small. Retrieved document instructions are untrusted and must not override system instructions.',['embedding','untrusted']),
 ('comparison','How are a file-size restriction and a retrieval-depth restriction different in the guide?','Uploads are limited to 20 MB per file; retrieval depth limits the chunks passed to generation.',['size','depth']),
 ('distracting_keywords','Leaving the review-window and API-port details aside, what time standard and days are specified for support opening?','Support opens at 09:00 UTC on weekdays.',['opening']),
 ('multi_chunk','What must remain backend-only, and what happens to vectors and metadata when a source is deleted?','API credentials remain backend-only. Deletion removes vectors and SQLite metadata.',['credentials','delete']),
 ('unanswerable','What holiday calendar overrides the support weekday schedule?','No holiday calendar is specified in the documents.',[]),
 ('unanswerable','How frequently are ChromaDB backups scheduled?','No ChromaDB backup schedule is specified in the documents.',[]),
 ('unanswerable','What penalty applies if a review exceeds 14 days?','No penalty for exceeding the review window is specified.',[]),
 ('unanswerable','Which cipher encrypts stored API credentials?','The documents do not specify a credential-encryption cipher.',[])]

def build_rows(specifications, split: str) -> list[dict]:
    catalog=source_catalog()
    rows=[]
    for number,(category,question,reference,keys) in enumerate(specifications,1):
        evidence=[]
        for key in keys:
            filename,page,quote=FACTS[key]
            matches=[row['chunk_id'] for row in catalog if row['filename']==filename and row['page']==page and normalize(quote) in row['text']]
            if not matches:
                raise ValueError(f'Missing independently verifiable quote: {key}')
            evidence.append({'fact_id':key,'filename':filename,'page':page,'quote':quote,'acceptable_chunk_ids':matches})
        rows.append({'id':f"{'ho' if split=='held_out' else 'final'}-{number:03}",'split':split,'category':category,
                     'question':question,'answerable':bool(keys),'reference_answer':reference,
                     'expected_sources':sorted({e['filename'] for e in evidence}),'evidence':evidence,
                     'expected_evidence':' '.join(e['quote'] for e in evidence),
                     'annotation_note':'Derived arithmetic: 8000-3000=5000.' if question.startswith('Which service uses') else '14 days = two 7-day weeks.' if question.startswith('Which passage supports') else 'Source-quoted facts or an explicitly labeled absence in the complete corpus.'})
    return rows

def validate_rows(rows: list[dict], catalog: list[dict], original_questions: set[str]) -> None:
    questions=set()
    chunks={row['chunk_id']:row for row in catalog}
    for row in rows:
        if row['question'] in questions or row['question'] in original_questions:
            raise ValueError('Duplicate or development question in held-out data')
        questions.add(row['question'])
        if row['answerable'] != bool(row['evidence']) or row['expected_sources'] != sorted({e['filename'] for e in row['evidence']}):
            raise ValueError('Inconsistent answerability/evidence labels')
        for evidence in row['evidence']:
            if not evidence['acceptable_chunk_ids']:
                raise ValueError('Evidence must have at least one acceptable chunk')
            for chunk_id in evidence['acceptable_chunk_ids']:
                chunk=chunks[chunk_id]
                if chunk['filename']!=evidence['filename'] or chunk['page']!=evidence['page'] or normalize(evidence['quote']) not in chunk['text']:
                    raise ValueError('Evidence quote or page mismatch')

def create(output: Path) -> dict:
    from ..rag import SYSTEM_PROMPT
    held=build_rows(HELDOUT,'held_out'); final=build_rows(FINAL,'final_test')
    original={json.loads(line)['question'] for line in (config.BASE_DIR/'evals/sample.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()}
    validate_rows(held+final,source_catalog(),original)
    output.mkdir(parents=True,exist_ok=True)
    for name,rows in [('heldout_v1.jsonl',held),('final_test_v1.jsonl',final)]:
        data=('\n'.join(json.dumps(row,ensure_ascii=True) for row in rows)+'\n').encode()
        path=output/name
        if path.exists() and path.read_bytes()!=data:
            raise ValueError('Refusing to replace a frozen dataset')
        path.write_bytes(data)
    protocol={'version':'question_holdout_v1','created_date':'2026-10-29','heldout_count':len(held),'final_test_count':len(final),
              'heldout_sha256':fingerprint(held),'final_test_sha256':fingerprint(final),'corpus_sha256':fingerprint(source_catalog()),
              'prompt_sha256':hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest(),'generation_prompt':SYSTEM_PROMPT,
              'chat_model':config.CHAT_MODEL,'embedding_model':config.EMBEDDING_MODEL,'reranker':'lightweight',
              'source_code_sha256':{name:hashlib.sha256((config.BASE_DIR/name).read_text(encoding='utf-8').encode()).hexdigest() for name in ['app/rag.py','app/retrieval.py','app/chunking.py']},
              'configurations':[{'mode':'dense','candidates':20,'top_k':5,'threshold':0.0},{'mode':'hybrid','candidates':20,'top_k':5,'threshold':0.0},{'mode':'hybrid_rerank','candidates':20,'top_k':5,'threshold':0.2}],
              'selection_policy':'Frozen before evaluation. No threshold calibration, model selection, prompt changes, or reranker-weight tuning on held-out answers. Final test is reserved and unexecuted.',
              'scope':'New questions over the known five-chunk public corpus; not unseen-document/domain generalization or blind external annotation.'}
    path=output/'protocol.json'
    if path.exists() and json.loads(path.read_text())!=protocol:
        raise ValueError('Refusing to replace a frozen protocol')
    path.write_text(json.dumps(protocol,indent=2)+'\n',encoding='utf-8')
    return protocol

if __name__=='__main__':
    print(json.dumps(create(config.BASE_DIR/'evals/heldout'),indent=2))
