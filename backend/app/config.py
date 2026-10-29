import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / '.env')

CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4.1-mini")
EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
CHROMA_PATH = os.getenv("CHROMA_PATH", "./data/chroma")
SQLITE_PATH = os.getenv("SQLITE_PATH", "./data/metadata.sqlite3")
CORS_ORIGINS = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if origin.strip()]
ALLOWED_HOSTS = [host.strip() for host in os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver').split(',') if host.strip()]
if os.getenv('RENDER_EXTERNAL_HOSTNAME'):
    ALLOWED_HOSTS.append(os.environ['RENDER_EXTERNAL_HOSTNAME'])
if '*' in CORS_ORIGINS or '*' in ALLOWED_HOSTS:
    raise ValueError('Configure explicit origins and hosts instead of a wildcard')
EVALUATION_PATH = Path(os.getenv('EVALUATION_PATH', str(BASE_DIR / 'evals' / 'results.json')))
MAX_UPLOAD_BYTES = 20 * 1024 * 1024

def flag(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {'1', 'true', 'yes'}

RETRIEVAL_MODE = os.getenv('RETRIEVAL_MODE', 'hybrid')
CANDIDATE_COUNT = int(os.getenv('RETRIEVAL_CANDIDATES', '20'))
FINAL_TOP_K = int(os.getenv('RETRIEVAL_TOP_K', '5'))
RELEVANCE_THRESHOLD = float(os.getenv('RELEVANCE_THRESHOLD', '0.2'))
RERANKER = os.getenv('RERANKER', 'lightweight')
RERANKER_MODEL = os.getenv('RERANKER_MODEL', '')
OPENAI_TIMEOUT = float(os.getenv('OPENAI_TIMEOUT_SECONDS', '45'))
OPENAI_RETRIES = int(os.getenv('OPENAI_MAX_RETRIES', '2'))
RATE_LIMIT_REQUESTS = int(os.getenv('RATE_LIMIT_REQUESTS', '60'))
RATE_LIMIT_WINDOW = int(os.getenv('RATE_LIMIT_WINDOW_SECONDS', '60'))
METRICS_RETENTION_DAYS = int(os.getenv('METRICS_RETENTION_DAYS', '30'))
LOG_QUERY_TEXT = flag('LOG_QUERY_TEXT')
MAX_PDF_PAGES = int(os.getenv('MAX_PDF_PAGES', '200'))
MAX_CHUNKS = int(os.getenv('MAX_CHUNKS_PER_UPLOAD', '500'))
MAX_EXTRACTED_CHARS = int(os.getenv('MAX_EXTRACTED_CHARS', '2000000'))
MAX_KEYWORD_CHUNKS = int(os.getenv('MAX_KEYWORD_CHUNKS', '50000'))
CHAT_INPUT_PRICE = os.getenv('CHAT_INPUT_USD_PER_MILLION')
CHAT_OUTPUT_PRICE = os.getenv('CHAT_OUTPUT_USD_PER_MILLION')
EMBEDDING_PRICE = os.getenv('EMBEDDING_USD_PER_MILLION')
EVALUATION_HISTORY_PATH = Path(os.getenv('EVALUATION_HISTORY_PATH', str(BASE_DIR / 'evals' / 'runs')))

# Safe on a fresh deployment: showcase routes never use the private corpus or API.
ACCESS_MODE = os.getenv('CITERAG_ACCESS_MODE', 'showcase')
ACCESS_TOKEN = os.getenv('CITERAG_ACCESS_TOKEN', '')
MAX_OUTPUT_TOKENS = int(os.getenv('MAX_OUTPUT_TOKENS', '800'))
MAX_CONTEXT_CHARS = int(os.getenv('MAX_CONTEXT_CHARS', '24000'))
DAILY_REQUEST_LIMIT = int(os.getenv('DAILY_REQUEST_LIMIT', '50'))
DAILY_TOKEN_LIMIT = int(os.getenv('DAILY_TOKEN_LIMIT', '200000'))
DAILY_USD_LIMIT = float(os.getenv('DAILY_USD_LIMIT', '1'))
MAX_STORED_CHUNKS = int(os.getenv('MAX_STORED_CHUNKS', '5000'))
if ACCESS_MODE not in {'showcase', 'live'}:
    raise ValueError('CITERAG_ACCESS_MODE must be showcase or live')
if not (1 <= MAX_OUTPUT_TOKENS <= 4096 and 1000 <= MAX_CONTEXT_CHARS <= 50000
        and DAILY_REQUEST_LIMIT > 0 and DAILY_TOKEN_LIMIT > 0 and 0 < DAILY_USD_LIMIT <= 100
        and MAX_STORED_CHUNKS > 0):
    raise ValueError('Invalid live usage bounds')

if RETRIEVAL_MODE not in {'dense', 'hybrid', 'hybrid_rerank'}:
    raise ValueError('RETRIEVAL_MODE must be dense, hybrid, or hybrid_rerank')
if not (1 <= FINAL_TOP_K <= 12 and 1 <= CANDIDATE_COUNT <= 100 and 0 <= RELEVANCE_THRESHOLD <= 1):
    raise ValueError('Invalid retrieval configuration bounds')
if not (0 < OPENAI_TIMEOUT <= 180 and 0 <= OPENAI_RETRIES <= 5 and METRICS_RETENTION_DAYS > 0 and RATE_LIMIT_WINDOW > 0):
    raise ValueError('Invalid timeout, retry, retention, or rate-limit window')

def ensure_data_dirs() -> None:
    Path(CHROMA_PATH).mkdir(parents=True, exist_ok=True)
    Path(SQLITE_PATH).parent.mkdir(parents=True, exist_ok=True)

