from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.api import router as core_router
from app.config import settings
from app.database import Base, engine
from app.phase3 import router as cases_router\nfrom app.phase4 import router as navigation_router\nfrom app.phase5 import router as tenant_router


def create_app() -> FastAPI:
    Base.metadata.create_all(bind=engine)
    app = FastAPI(
        title="Enesko",
        version="0.5.0",
        description="Enesko Phases 1-5 backend: mall core, knowledge, cases, indoor navigation and tenant platform",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["System"])
    def health():
        return {"status": "ok", "service": "Enesko", "implemented_phases": [1, 2, 3, 4, 5]}

    @app.get("/", include_in_schema=False)
    def test_page():
        return FileResponse(Path(__file__).parent / "static" / "index.html")

    app.include_router(core_router)
    app.include_router(cases_router)
    return app


app = create_app()
