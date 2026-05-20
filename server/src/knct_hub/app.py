import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from knct_hub.api import hooks, kpatches, orgs, projects
from knct_hub.config import get_settings

logger = logging.getLogger(__name__)


def _run_migrations() -> None:
    server_root = Path(__file__).resolve().parents[2]
    ini_path = server_root / "alembic.ini"
    cfg = Config(str(ini_path))
    cfg.set_main_option("script_location", str(server_root / "alembic"))
    cfg.set_main_option("sqlalchemy.url", get_settings().database_url)
    command.upgrade(cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if settings.auto_migrate:
        logger.info("running alembic upgrade head")
        await asyncio.to_thread(_run_migrations)
    yield


def _mount_dashboard(app: FastAPI, dist: Path) -> None:
    """Serve the built dashboard at / with SPA fallback for client-side routes."""
    assets = dist / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    index = dist / "index.html"

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str):
        if full_path.startswith("api"):
            raise HTTPException(status_code=404)
        # Serve real files at root (favicon, robots.txt, etc.)
        if full_path:
            candidate = dist / full_path
            if candidate.is_file():
                return FileResponse(candidate)
        return FileResponse(index)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="knct-hub", lifespan=lifespan)

    # Health endpoint (under /api/v1 for consistency).
    health = APIRouter()

    @health.get("/health")
    def _health() -> dict:
        return {"ok": True}

    for router in (
        hooks.router,
        orgs.router,
        kpatches.router,
        projects.router,
        health,
    ):
        app.include_router(router, prefix="/api/v1")

    dist = Path(settings.dashboard_dist)
    if dist.is_dir() and (dist / "index.html").is_file():
        _mount_dashboard(app, dist)
    else:
        logger.info("dashboard dist not found at %s; UI will not be served", dist)

    return app


app = create_app()
