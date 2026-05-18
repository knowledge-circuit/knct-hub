import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import FastAPI

from knct_hub.api import hooks, projects, rules, skills
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


def create_app() -> FastAPI:
    app = FastAPI(title="knct-hub", lifespan=lifespan)
    for router in (hooks.router, projects.router, skills.router, rules.router):
        app.include_router(router, prefix="/api/v1")
    return app


app = create_app()
