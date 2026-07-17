from __future__ import annotations

import os
from pathlib import Path

from worldcup_agent.runtime.service import AgentRuntimeService
from worldcup_agent.storage.sqlite import SQLiteRunStore
from worldcup_agent.tools.demo import build_demo_registry
from worldcup_agent.tools.production import ProductionServices, build_production_registry


async def build_service(
    path: str | Path,
    mode: str = "demo",
    artifacts_dir: str | None = None,
    rules_dir: str | None = None,
) -> AgentRuntimeService:
    store = SQLiteRunStore(path)
    await store.initialize()
    if mode in {"portfolio", "production"}:
        if mode == "production" and (artifacts_dir or os.getenv("WORLDCUP_MODEL_ARTIFACTS_DIR")):
            services = ProductionServices.from_artifacts(
                artifacts_dir or os.environ["WORLDCUP_MODEL_ARTIFACTS_DIR"],
                rules_dir or os.getenv("WORLDCUP_RULES_DIR", "rules/fifa_2026"),
            )
        else:
            services = ProductionServices.fixture()
        registry = build_production_registry(services)
        return AgentRuntimeService(store, registry, planner=None, production=True)
    return AgentRuntimeService(store, build_demo_registry())
