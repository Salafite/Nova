import os
import sys
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(ROOT_DIR))

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from modules.core.controllers import all_routers
from packages.auth.controller import router as auth_router
from packages.ws.handlers import router as ws_router
from packages.billing.controller import router as billing_router
from modules.bi.controllers.dashboard import router as bi_dashboard_router
from packages.rate_limit import RateLimitMiddleware
from packages.analytics.sentry import init_sentry
from packages.cache.middleware import CacheControlMiddleware
from packages.security.middleware import SecurityHeadersMiddleware
from packages.mcp.server import McpServer
from packages.ai.router import router as ai_router
from packages.mcp.router import create_mcp_router
from packages.mcp.servers.database_mcp import register_tools as register_database_mcp
from packages.mcp.servers.inventory_mcp import register_tools as register_inventory_mcp
from packages.mcp.servers.sales_mcp import register_tools as register_sales_mcp
from packages.mcp.servers.purchasing_mcp import register_tools as register_purchasing_mcp
from packages.mcp.servers.accounting_mcp import register_tools as register_accounting_mcp
from packages.mcp.servers.admin_mcp import register_tools as register_admin_mcp
from packages.mcp.servers.warehouse_mcp import register_tools as register_warehouse_mcp
from packages.mcp.servers.hr_mcp import register_tools as register_hr_mcp
from packages.mcp.servers.bi_mcp import register_tools as register_bi_mcp
from packages.mcp.servers.crm_mcp import register_tools as register_crm_mcp
from packages.mcp.servers.projects_mcp import register_tools as register_projects_mcp
from packages.mcp.servers.manufacturing_mcp import register_tools as register_manufacturing_mcp
from packages.mcp.servers.maintenance_mcp import register_tools as register_maintenance_mcp
from packages.mcp.servers.notifications_mcp import register_tools as register_notifications_mcp
from packages.mcp.servers.pos_mcp import register_tools as register_pos_mcp
from modules.administration.controllers.user_preferences import router as user_preferences_router
from modules.administration.controllers.admin_preferences import router as admin_preferences_router

app = FastAPI(title="Nova ERP API", version="1.0")
init_sentry()

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
app.include_router(bi_dashboard_router)
app.include_router(ai_router)
app.include_router(user_preferences_router)
app.include_router(admin_preferences_router)

mcp_server = McpServer(name="NovaERP", version="1.0")
register_database_mcp()
register_inventory_mcp()
register_sales_mcp()
register_purchasing_mcp()
register_accounting_mcp()
register_admin_mcp()
register_warehouse_mcp()
register_hr_mcp()
register_bi_mcp()
register_crm_mcp()
register_projects_mcp()
register_manufacturing_mcp()
register_maintenance_mcp()
register_notifications_mcp()
register_pos_mcp()
app.include_router(create_mcp_router(mcp_server))


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
        if full_path.startswith('api/'):
            return JSONResponse({'detail': 'Not Found'}, status_code=404)
        file_path = STATIC_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        index = STATIC_DIR / "index.html"
        if index.exists():
            return FileResponse(str(index))
        return {"error": "Not found"}


if __name__ == '__main__':
    import uvicorn
    is_prod = os.getenv('NOVA_ENV') == 'production'
    uvicorn.run('main:app', host='0.0.0.0', port=8070, reload=not is_prod, workers=4 if is_prod else 1)
