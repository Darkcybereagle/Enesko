from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from app.api import router as core_router
from app.auth_api import router as auth_router
from app.platform_api import router as platform_router
from app.audit import audit_mutations
from app.config import settings
from app.database import Base,engine
from app.phase3 import router as cases_router
from app.phase4 import router as navigation_router
from app.phase5 import router as tenant_router
from app.phase6 import router as activations_router
from app.phase7 import router as channels_router
from app.phase8 import router as voice_router
from app.phase9 import router as cinema_router
from app.phase10 import router as parking_router
from app.phase11 import router as parking_integration_router
from app.phase12 import router as smart_parking_router
from app.phase13 import router as analytics_router

def create_app()->FastAPI:
    if settings.app_env != "production": Base.metadata.create_all(bind=engine)
    app=FastAPI(title="Enesko",version="0.20.0",description="ENESKO Category 2 — secured platform and product interfaces")
    app.add_middleware(CORSMiddleware,allow_origins=settings.cors_origin_list,allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
    app.middleware("http")(audit_mutations)
    @app.get("/health",tags=["System"])
    def health(): return {"status":"ok","service":"Enesko","category":2,"implemented_phases":list(range(1,14)),"platform":["migrations","auth","rbac","audit","customer-web","admin-dashboard","tenant-portal"]}
    @app.get("/",include_in_schema=False)
    def test_page(): return FileResponse(Path(__file__).parent/"static"/"index.html")
    for router in (auth_router,platform_router,core_router,cases_router,navigation_router,tenant_router,activations_router,channels_router,voice_router,cinema_router,parking_router,parking_integration_router,smart_parking_router,analytics_router):
        app.include_router(router)
    return app
app=create_app()
