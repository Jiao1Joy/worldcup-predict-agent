from __future__ import annotations

from pathlib import Path

from worldcup_agent.runtime.service import AgentRuntimeService
from worldcup_agent.storage.sqlite import SQLiteRunStore
from worldcup_agent.tools.demo import build_demo_registry
from worldcup_agent.tools.production import ProductionServices, build_production_registry


async def build_service(path: str | Path, mode: str = "demo") -> AgentRuntimeService:
    store = SQLiteRunStore(path)
    await store.initialize()
    if mode == "production":
        registry = build_production_registry(ProductionServices.fixture())
        return AgentRuntimeService(store, registry, planner=None, production=True)
    return AgentRuntimeService(store, build_demo_registry())
