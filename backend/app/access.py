"""Single-owner bearer authentication; no unauthenticated live data routes."""
import secrets
from starlette.responses import JSONResponse
from . import config


def authenticated(request) -> bool:
    token = config.ACCESS_TOKEN
    supplied = request.headers.get('authorization', '')
    return (len(token) >= 32 and supplied.startswith('Bearer ')
            and secrets.compare_digest(supplied[7:].encode(), token.encode()))


def authorize(request):
    if request.method == 'OPTIONS' or request.url.path in {'/health', '/session'}:
        return None
    if config.ACCESS_MODE == 'showcase':
        reads = {'/documents', '/retrieval/config', '/evaluations', '/evaluations/runs', '/showcase/questions'}
        if request.method == 'GET' and (request.url.path in reads or request.url.path.startswith('/evaluations/runs/')):
            return None
        if request.method == 'POST' and request.url.path == '/chat':
            return None
        return JSONResponse({'detail': 'Showcase is read-only. Owner live access is required.'}, 403)
    if len(config.ACCESS_TOKEN) < 32:
        return JSONResponse({'detail': 'Live access is disabled until the owner configures a strong access token.'}, 503)
    if not authenticated(request):
        return JSONResponse({'detail': 'Owner authentication required.'}, 401, headers={'WWW-Authenticate': 'Bearer'})
    return None
