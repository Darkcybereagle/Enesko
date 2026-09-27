from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.api import router as core_router
from app.config import settings
from app.database import Base, engine
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

def create_app() -> FastAPI:
    Base.metadata.create_all(bind=engine)
    app = FastAPI(
        title="Enesko", version="0.13.0",
        description="ENESKO intelligent mall operations backend — Phases 1-13",
    )
    app.add_middleware(
        CORSMiddleware, allow_origins=settings.cors_origin_list,
        allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
    )

    @app.get("/health", tags=["System"])
    def health():
        return {"status":"ok","service":"Enesko","implemented_phases":list(range(1,14))}

    @app.get("/", include_in_schema=False)
    def test_page():
        return FileResponse(Path(__file__).parent / "static" / "index.html")

    for router in (
        core_router, cases_router, navigation_router, tenant_router, activations_router,
        channels_router, voice_router, cinema_router, parking_router,
        parking_integration_router, smart_parking_router, analytics_router,
    ):
        app.include_router(router)
    return app

app=create_app()
