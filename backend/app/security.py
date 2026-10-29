from collections import defaultdict, deque
import re
from threading import Lock
import time
import unicodedata
from pathlib import PurePosixPath, PureWindowsPath
from . import config
from starlette.exceptions import HTTPException

class BodySizeLimitMiddleware:
    """Bound streamed bodies too, including chunked uploads without Content-Length."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope['method'] != 'POST':
            return await self.app(scope, receive, send)
        received = 0
        async def limited_receive():
            nonlocal received
            message = await receive()
            if message['type'] == 'http.request':
                received += len(message.get('body', b''))
                if received > config.MAX_UPLOAD_BYTES + 1024*1024:
                    raise HTTPException(413, 'Request body exceeds upload limit')
            return message
        await self.app(scope, limited_receive, send)

def safe_filename(filename: str | None) -> str:
    name = PurePosixPath(PureWindowsPath(filename or '').name).name
    name = ''.join(char for char in name if not unicodedata.category(char).startswith('C')).strip(' .')
    if not name or len(name) > 160:
        raise ValueError('Filename must contain 1 to 160 printable characters')
    return name

class RateLimiter:
    """Per-process sliding window; deployment still needs an edge/global limiter."""
    def __init__(self):
        self.requests = defaultdict(deque)
        self.lock = Lock()

    def allow(self, identity: str) -> bool:
        limit, window, now = config.RATE_LIMIT_REQUESTS, config.RATE_LIMIT_WINDOW, time.monotonic()
        if limit <= 0:
            return True
        with self.lock:
            for key in list(self.requests):
                if not self.requests[key] or self.requests[key][-1] <= now-window:
                    del self.requests[key]
            if identity not in self.requests and len(self.requests) >= 10000:
                return False
            events = self.requests[identity]
            while events and events[0] <= now-window:
                events.popleft()
            if len(events) >= limit:
                return False
            events.append(now)
            return True
