from datetime import UTC, datetime
from pathlib import Path

import aiosqlite

from worldcup_agent.domain.models import Checkpoint, EvidenceItem, RunEvent, RunState


class SQLiteRunStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    async def initialize(self) -> None:
        schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
        async with aiosqlite.connect(self.path) as db:
            await db.executescript(schema)
            await db.commit()

    async def create_run(self, state: RunState) -> None:
        now = datetime.now(UTC).isoformat()
        payload = state.model_dump_json()
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT INTO runs VALUES (?, ?, ?, ?, ?)",
                (state.run_id, payload, payload, now, now),
            )
            await db.commit()

    async def append_event(self, event: RunEvent) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT INTO events VALUES (?, ?, ?)",
                (event.run_id, event.sequence, event.model_dump_json()),
            )
            await db.commit()

    async def list_events(self, run_id: str, after: int = 0) -> list[RunEvent]:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "SELECT event_json FROM events WHERE run_id=? AND sequence>? ORDER BY sequence",
                (run_id, after),
            )
            rows = await cursor.fetchall()
        return [RunEvent.model_validate_json(row[0]) for row in rows]

    async def get_initial_state(self, run_id: str) -> RunState:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "SELECT initial_state_json FROM runs WHERE run_id=?",
                (run_id,),
            )
            row = await cursor.fetchone()
        if row is None:
            raise KeyError(run_id)
        return RunState.model_validate_json(row[0])

    async def get_current_state(self, run_id: str) -> RunState:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "SELECT current_state_json FROM runs WHERE run_id=?",
                (run_id,),
            )
            row = await cursor.fetchone()
        if row is None:
            raise KeyError(run_id)
        return RunState.model_validate_json(row[0])

    async def save_evidence(self, run_id: str, evidence: EvidenceItem) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO evidence VALUES (?, ?, ?)",
                (evidence.evidence_id, run_id, evidence.model_dump_json()),
            )
            await db.commit()

    async def list_evidence(self, run_id: str) -> list[EvidenceItem]:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "SELECT evidence_json FROM evidence WHERE run_id=? ORDER BY evidence_id",
                (run_id,),
            )
            rows = await cursor.fetchall()
        return [EvidenceItem.model_validate_json(row[0]) for row in rows]

    async def save_checkpoint(self, checkpoint: Checkpoint) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO checkpoints VALUES (?, ?, ?, ?)",
                (
                    checkpoint.checkpoint_id,
                    checkpoint.run_id,
                    checkpoint.sequence,
                    checkpoint.model_dump_json(),
                ),
            )
            await db.commit()

    async def latest_checkpoint(self, run_id: str) -> Checkpoint | None:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "SELECT checkpoint_json FROM checkpoints WHERE run_id=? ORDER BY sequence DESC LIMIT 1",
                (run_id,),
            )
            row = await cursor.fetchone()
        return Checkpoint.model_validate_json(row[0]) if row else None

    async def update_current_state(self, state: RunState) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "UPDATE runs SET current_state_json=?, updated_at=? WHERE run_id=?",
                (state.model_dump_json(), datetime.now(UTC).isoformat(), state.run_id),
            )
            await db.commit()
