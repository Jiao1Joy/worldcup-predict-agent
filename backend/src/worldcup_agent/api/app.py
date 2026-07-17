from contextlib import asynccontextmanager
import json
import os
from pathlib import Path

from fastapi import FastAPI

from worldcup_agent.api.dependencies import build_service
from worldcup_agent.api.routes.backtests import router as backtests_router
from worldcup_agent.api.routes.forecasts import router as forecasts_router
from worldcup_agent.api.routes.health import router as health_router
from worldcup_agent.api.routes.runs import router as runs_router
from worldcup_agent.forecasts.repository import ForecastRepository
from worldcup_agent.forecasts.service import ForecastService


def create_app(
    sqlite_path: str | Path = "agent.sqlite3",
    mode: str = "demo",
    forecasts_dir: str | Path | None = None,
    model_artifacts_dir: str | None = None,
    rules_dir: str | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.runtime_service = await build_service(
            sqlite_path,
            mode=mode,
            artifacts_dir=model_artifacts_dir,
            rules_dir=rules_dir,
        )
        if forecasts_dir is not None:
            forecast_root = Path(forecasts_dir)
            app.state.forecast_service = ForecastService(ForecastRepository(forecast_root))
            backtest_path = forecast_root / "backtest-2022.json"
            if backtest_path.exists():
                app.state.backtest_2022 = json.loads(backtest_path.read_text(encoding="utf-8"))
        yield

    app = FastAPI(title="World Cup Prediction Agent", lifespan=lifespan)
    app.include_router(health_router)
    app.include_router(runs_router)
    app.include_router(forecasts_router)
    app.include_router(backtests_router)
    return app


app = create_app(
    sqlite_path=os.getenv("WORLDCUP_SQLITE_PATH", "agent.sqlite3"),
    mode=os.getenv("WORLDCUP_MODE", "demo"),
    forecasts_dir=os.getenv("WORLDCUP_ARTIFACTS_DIR"),
    model_artifacts_dir=os.getenv("WORLDCUP_MODEL_ARTIFACTS_DIR"),
    rules_dir=os.getenv("WORLDCUP_RULES_DIR"),
)
