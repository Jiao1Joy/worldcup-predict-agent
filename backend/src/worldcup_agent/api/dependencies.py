from pathlib import Path

from worldcup_agent.runtime.service import AgentRuntimeService
from worldcup_agent.storage.sqlite import SQLiteRunStore
from worldcup_agent.tools.demo import build_demo_registry


async def build_service(path: str | Path) -> AgentRuntimeService:
    store = SQLiteRunStore(path)
    await store.initialize()
    return AgentRuntimeService(store, build_demo_registry())
