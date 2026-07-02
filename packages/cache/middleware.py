from starlette.middleware.base import BaseHTTPMiddleware


class CacheControlMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if request.method == 'GET' and response.status_code == 200:
            if request.url.path.startswith('/api/'):
                if '/health' in request.url.path:
                    response.headers['Cache-Control'] = 'no-cache'
                else:
                    response.headers['Cache-Control'] = 'private, max-age=30'
            elif any(request.url.path.startswith(p) for p in ('/assets/', '/icons/', '/manifest.json')):
                response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        return response
