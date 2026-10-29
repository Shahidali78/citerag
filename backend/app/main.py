from io import BytesIO
from pathlib import Path
from uuid import uuid4
import json
import logging
import os
import time
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
from datetime import datetime, timezone
from fastapi import FastAPI, File, HTTPException, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pypdf import PdfReader
from . import config
from .chunking import chunk_pages
from .rag import answer_question
from .schemas import ChatRequest, ChatResponse, DocumentInfo
from .store import delete_document, list_documents, save_document, log_query
from .provider import get_client, demo_enabled
from .observability import Trace, active_trace, save_metric, monitoring
from .security import RateLimiter, safe_filename, BodySizeLimitMiddleware
from .retrieval import RetrievalOptions
from .access import authorize, authenticated
from . import showcase, budget

app = FastAPI(title="CiteRAG API", version="1.0.0")
app.add_middleware(BodySizeLimitMiddleware)
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger('citerag')
logging.getLogger('httpx').setLevel(logging.WARNING)
limiter = RateLimiter()

@app.middleware('http')
async def request_log(request, call_next):
    started = time.perf_counter()
    metric = Trace()
    token = active_trace.set(metric)
    status = 500
    try:
        denied = authorize(request)
        origin = request.headers.get('origin')
        trusted_origin = origin in config.CORS_ORIGINS or origin == str(request.base_url).rstrip('/')
        if denied is not None:
            response = denied if limiter.allow(request.client.host if request.client else 'unknown') else JSONResponse({'detail': 'Too many requests. Try again later.'}, 429)
        elif request.method in {'POST', 'DELETE'} and origin and not trusted_origin:
            response = JSONResponse({'detail': 'Request origin is not allowed'}, 403)
        elif request.method in {'POST', 'DELETE'} and not limiter.allow(request.client.host if request.client else 'unknown'):
            response = JSONResponse({'detail': 'Too many requests. Try again later.'}, 429, headers={'Retry-After': str(config.RATE_LIMIT_WINDOW)})
        elif request.method == 'POST' and request.headers.get('content-length', '').isdigit() and int(request.headers['content-length']) > config.MAX_UPLOAD_BYTES+1024*1024:
            response = JSONResponse({'detail': 'Request body exceeds upload limit'}, 413)
        else:
            if config.ACCESS_MODE == 'live' and request.method == 'POST' and request.url.path in {'/chat', '/documents'}:
                await run_in_threadpool(budget.reserve, requests=1)
            response = await call_next(request)
        status = response.status_code
    except HTTPException as exc:
        status = exc.status_code
        response = JSONResponse({'detail': exc.detail}, status)
    except Exception:
        # Do not serialize exception text, request bodies, or provider payloads.
        response = JSONResponse({'detail': 'Internal server error. Refer to the request ID.'}, 500)
    finally:
        active_trace.reset(token)
        endpoint = getattr(request.scope.get('route'), 'path', 'unmatched')
        if request.url.path in {'/health', '/monitoring', '/docs', '/openapi.json', '/redoc'}:
            endpoint = request.url.path
        if config.ACCESS_MODE == 'live' and authenticated(request) and endpoint not in {'/health', '/session', '/monitoring', '/docs', '/openapi.json', '/redoc'}:
            record = {**metric.snapshot(), 'provider_mode': 'demo' if demo_enabled() else 'openai', 'timestamp': datetime.now(timezone.utc).isoformat(), 'endpoint': endpoint,
                      'method': request.method, 'status': status, 'success': status < 400, 'latency_seconds': round(time.perf_counter()-started, 6)}
            try:
                await run_in_threadpool(save_metric, record)
            except Exception:
                logger.error(json.dumps({'event': 'metrics_write_failed', 'request_id': metric.request_id}))
    response.headers['X-Request-ID'] = metric.request_id
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Cache-Control'] = 'no-store'
    return response

def require_key():
    if not demo_enabled() and not os.getenv('OPENAI_API_KEY'):
        raise HTTPException(503, 'Set OPENAI_API_KEY in backend/.env and restart the backend.')
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_credentials=False, allow_methods=["GET", "POST", "DELETE"], allow_headers=["Content-Type", "Authorization"], expose_headers=['X-Request-ID'])
app.add_middleware(TrustedHostMiddleware, allowed_hosts=config.ALLOWED_HOSTS)

@app.get("/health")
def health():
    return {"status": "ok", "openai_configured": config.ACCESS_MODE == 'live' and bool(os.getenv('OPENAI_API_KEY')), 'mode': 'showcase' if config.ACCESS_MODE == 'showcase' else 'demo' if demo_enabled() else 'openai'}

@app.get('/session')
def session(request: Request):
    return {'access_mode': config.ACCESS_MODE, 'authenticated': authenticated(request),
            'live_configured': len(config.ACCESS_TOKEN) >= 32, 'provider_mode': health()['mode']}

@app.get('/auth')
def auth():
    return {'authenticated': True}

@app.get('/showcase/questions')
def sample_questions():
    return showcase.questions()

@app.get('/monitoring')
def metrics_dashboard():
    return {**monitoring(), 'daily_budget': budget.summary()}

@app.get('/retrieval/config')
def retrieval_config():
    return {'default': RetrievalOptions.defaults().__dict__, 'modes': ['dense', 'hybrid', 'hybrid_rerank'], 'reranker': config.RERANKER,
            'score_note': 'Cosine, BM25, RRF, and reranker scores are ranking signals, not factual probabilities.'}

@app.get('/evaluations/runs')
def evaluation_history():
    if config.ACCESS_MODE == 'showcase':
        return showcase.runs()
    from .eval.history import list_runs
    return list_runs()

@app.get('/evaluations/runs/{run_id}')
def evaluation_run(run_id: str):
    if config.ACCESS_MODE == 'showcase':
        return showcase.read_run(run_id)
    from .eval.history import read_run
    try:
        return read_run(run_id)
    except (ValueError, FileNotFoundError):
        raise HTTPException(404, 'Evaluation run not found')

@app.get('/evaluations')
def evaluations():
    if config.ACCESS_MODE == 'showcase':
        return {'available': True, **showcase.report()}
    if not config.EVALUATION_PATH.exists():
        return {'available': False, 'message': 'No saved run. Follow the evaluation commands in README.md.'}
    try:
        return {'available': True, **json.loads(config.EVALUATION_PATH.read_text(encoding='utf-8'))}
    except (ValueError, OSError):
        raise HTTPException(500, 'Saved evaluation report could not be read.')

@app.get("/documents", response_model=list[DocumentInfo])
def documents():
    if config.ACCESS_MODE == 'showcase':
        return showcase.documents()
    return list_documents()

@app.delete("/documents/{document_id}")
def remove_document(document_id: str):
    if not delete_document(document_id):
        raise HTTPException(status_code=404, detail="Document not found")
    return {"deleted": True}

@app.post("/documents", response_model=DocumentInfo, status_code=201)
async def upload_document(file: UploadFile = File(...)):
    try:
        filename = safe_filename(file.filename)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    suffix = Path(filename).suffix.lower()
    if suffix not in {".pdf", ".txt", ".md"}:
        raise HTTPException(status_code=415, detail="Only PDF, TXT, and MD files are supported")
    data = await file.read(config.MAX_UPLOAD_BYTES + 1)
    if len(data) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 20 MB")
    try:
        if suffix == ".pdf":
            def extract_pdf():
                reader = PdfReader(BytesIO(data))
                if len(reader.pages) > config.MAX_PDF_PAGES:
                    raise ValueError('Too many PDF pages')
                pages = []
                length = 0
                for page in reader.pages:
                    text = page.extract_text() or ''
                    length += len(text)
                    if length > config.MAX_EXTRACTED_CHARS:
                        raise ValueError('Extracted text exceeds resource limit')
                    pages.append(text)
                return pages
            pages = await run_in_threadpool(extract_pdf)
        else:
            pages = [data.decode("utf-8-sig")]
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not extract text: {type(exc).__name__}") from exc
    if sum(map(len, pages)) > config.MAX_EXTRACTED_CHARS:
        raise HTTPException(422, 'Document exceeds indexing resource limits')
    chunks = await run_in_threadpool(chunk_pages, pages)
    if len(chunks) > config.MAX_CHUNKS:
        raise HTTPException(422, 'Document exceeds indexing resource limits')
    if not chunks:
        raise HTTPException(status_code=422, detail="No extractable text (scanned PDFs require OCR)")
    try:
        from .store import collection
        if collection().count() + len(chunks) > config.MAX_STORED_CHUNKS:
            raise HTTPException(422, 'Corpus capacity reached. Delete unused documents before uploading.')
        require_key()
        client = get_client()
        embeddings = []
        for offset in range(0, len(chunks), 100):
            batch = chunks[offset:offset+100]
            metrics = active_trace.get()
            with metrics.timed('embedding'):
                response = await run_in_threadpool(client.embeddings.create, model=config.EMBEDDING_MODEL, input=[chunk.text for chunk in batch])
            metrics.record_usage('embedding', response, config.EMBEDDING_MODEL)
            embeddings.extend(item.embedding for item in sorted(response.data, key=lambda item: item.index))
        doc_id = str(uuid4())
        await run_in_threadpool(save_document, doc_id, filename, [c.text for c in chunks], [c.page for c in chunks], embeddings)
        return next(d for d in list_documents() if d["id"] == doc_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(json.dumps({'event': 'ingestion_failed', 'error_type': type(exc).__name__}))
        raise HTTPException(status_code=502, detail='Ingestion failed. Check API credentials, model access, and backend logs.') from exc

@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    if config.ACCESS_MODE == 'showcase':
        return showcase.answer(request.question)
    try:
        options = RetrievalOptions(request.retrieval_mode or config.RETRIEVAL_MODE, request.candidate_count or config.CANDIDATE_COUNT, request.top_k,
                                   config.RELEVANCE_THRESHOLD if request.relevance_threshold is None else request.relevance_threshold)
        response = answer_question(request.question, request.top_k, retrieval_options=options)
        log_query(request.question, [c.chunk_id for c in response.retrieved_chunks])
        return response
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(json.dumps({'event': 'generation_failed', 'error_type': type(exc).__name__}))
        raise HTTPException(status_code=502, detail='Answer generation failed. Check API credentials, model access, and backend logs.') from exc

