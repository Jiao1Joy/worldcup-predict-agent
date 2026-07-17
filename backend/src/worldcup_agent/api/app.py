from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from worldcup_agent.api.dependencies import build_service
from worldcup_agent.api.routes.backtests import router as backtests_router
from worldcup_agent.api.routes.forecasts import router as forecasts_router
from worldcup_agent.api.routes.health import router as health_router
from worldcup_agent.api.routes.runs import router as runs_router
from worldcup_agent.forecasts.repository import ForecastRepository
from worldcup_agent.forecasts.service import ForecastService


def create_app(sqlite_path: str | Path = "agent.sqlite3", mode: str = "demo", forecasts_dir: str | Path | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.runtime_service = await build_service(sqlite_path, mode=mode)
        if forecasts_dir is not None:
            app.state.forecast_service = ForecastService(ForecastRepository(forecasts_dir))
        yield

    app = FastAPI(title="World Cup Prediction Agent", lifespan=lifespan)
    app.include_router(health_router)
    app.include_router(runs_router)
    app.include_router(forecasts_router)
    app.include_router(backtests_router)
    return app


app = create_app()
