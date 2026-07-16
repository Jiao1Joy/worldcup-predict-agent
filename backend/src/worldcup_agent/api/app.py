from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from worldcup_agent.api.dependencies import build_service
from worldcup_agent.api.routes.runs import router as runs_router


def create_app(sqlite_path: str | Path = "agent.sqlite3") -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.runtime_service = await build_service(sqlite_path)
        yield

    app = FastAPI(title="World Cup Prediction Agent", lifespan=lifespan)
    app.include_router(runs_router)
    return app


app = create_app()
