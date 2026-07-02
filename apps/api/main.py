import os
import sys
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(ROOT_DIR))

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from controllers import all_routers
from packages.auth.controller import router as auth_router
from packages.ws.handlers import router as ws_router
from packages.billing.controller import router as billing_router
from packages.rate_limit import RateLimitMiddleware
from packages.cache.middleware import CacheControlMiddleware
from packages.security.middleware import SecurityHeadersMiddleware

app = FastAPI(title="Nova ERP API", version="1.0")

origins = os.getenv('ALLOWED_ORIGINS', '*').split(',')

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(CacheControlMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])

for router in all_routers:
    app.include_router(router)

app.include_router(ws_router)
app.include_router(billing_router)


@app.get('/api')
def root():
    return {'message': 'Welcome to Nova ERP API'}


@app.get('/api/health')
def health_check():
    return {'status': 'ok', 'app': 'Nova App'}


# Serve Vue dist or legacy web
VUE_DIR = ROOT_DIR / "apps" / "web-vue" / "dist"
WEB_DIR = ROOT_DIR / "apps" / "web"
STATIC_DIR = VUE_DIR if VUE_DIR.exists() else (WEB_DIR if WEB_DIR.exists() else None)

if STATIC_DIR:
    # Mount /assets for Vite build outputs
    assets_dir = STATIC_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get('/{full_path:path}')
    async def serve_spa(full_path: str):
        file_path = STATIC_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        index = STATIC_DIR / "index.html"
        if index.exists():
            return FileResponse(str(index))
        return {"error": "Not found"}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run('main:app', host='0.0.0.0', port=8070, reload=True)
