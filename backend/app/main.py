from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.api import router
from app.config import settings
from app.database import Base, engine


def create_app() -> FastAPI:
    Base.metadata.create_all(bind=engine)
    app = FastAPI(
        title="Enesko",
        version="0.2.0",
        description="Enesko Phase 1 Mall Core + Phase 2 Knowledge and Conversational Core",
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
        return {"status": "ok", "service": "Enesko", "implemented_phases": [1, 2]}

    @app.get("/", include_in_schema=False)
    def test_page():
        return FileResponse(Path(__file__).parent / "static" / "index.html")

    app.include_router(router)
    return app


app = create_app()
