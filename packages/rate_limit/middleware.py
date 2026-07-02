import time
import threading
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

RATE_LIMITS = {
    'auth': (10, 1),
    'read': (100, 1),
    'write': (50, 1),
}


def _classify(path, method):
    if path.startswith('/api/auth/'):
        return 'auth'
    if method in ('GET',):
        return 'read'
    return 'write'


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._lock = threading.Lock()
        self._buckets = defaultdict(lambda: defaultdict(list))

    async def dispatch(self, request, call_next):
        client_ip = request.client.host if request.client else 'unknown'
        category = _classify(request.url.path, request.method)
        limit, window = RATE_LIMITS.get(category, (50, 1))
        now = time.time()

        with self._lock:
            bucket = self._buckets[client_ip][category]
            bucket[:] = [t for t in bucket if t > now - window]
            if len(bucket) >= limit:
                retry_after = int(bucket[0] - now + window) if bucket else 1
                return JSONResponse(
                    status_code=429,
                    content={'detail': 'Rate limit exceeded. Try again later.'},
                    headers={'Retry-After': str(max(retry_after, 1))},
                )
            bucket.append(now)

        response = await call_next(request)
        return response
