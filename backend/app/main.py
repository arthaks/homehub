from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .models import HealthResponse, PublicConfig, ReadyResponse, VersionResponse
from .settings import Settings
from .status_service import StatusUnavailableError, build_dashboard, load_public_config

settings = Settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(
    title="HomeHub API",
    version=settings.version,
    docs_url=None,
    redoc_url=None,
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(version=settings.version, commit=settings.commit)


@app.get("/api/version", response_model=VersionResponse)
def version() -> VersionResponse:
    return VersionResponse(
        version=settings.version,
        commit=settings.commit,
        buildTime=settings.build_time,
    )


@app.get("/api/ready", response_model=ReadyResponse)
def ready() -> ReadyResponse:
    try:
        dashboard = build_dashboard(settings)
    except StatusUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if dashboard.freshness == "stale":
        raise HTTPException(status_code=503, detail="status snapshot is stale")
    return ReadyResponse(
        status="ready",
        statusFileAvailable=True,
        statusFileFresh=dashboard.fresh,
        detail=None if dashboard.fresh else "status snapshot is delayed",
    )


@app.get("/api/dashboard")
def dashboard():
    try:
        return build_dashboard(settings)
    except StatusUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/config/public", response_model=PublicConfig)
def public_config() -> PublicConfig:
    try:
        config, _ = load_public_config(settings.config_file)
        return config
    except StatusUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


if settings.static_dir.exists():
    assets = settings.static_dir / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        requested = settings.static_dir / full_path
        if full_path and requested.is_file() and settings.static_dir in requested.resolve().parents:
            return FileResponse(requested)
        return FileResponse(settings.static_dir / "index.html")
