import argparse
import asyncio
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from worldcup_agent.api.dependencies import build_service


async def generate(output: Path) -> None:
    with TemporaryDirectory() as directory:
        service = await build_service(Path(directory) / "fixture.sqlite3")
        run = await service.create_run({"intent": "predict_tournament", "seed": 7})
        completed = await service.run(run.run_id)
        events = await service.store.list_events(run.run_id)
        output.write_text(
            json.dumps(
                {
                    "initial_state": run.model_copy(update={"event_sequence": 0}).model_dump(mode="json"),
                    "state": completed.model_dump(mode="json"),
                    "events": [event.model_dump(mode="json") for event in events],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(generate(args.output))


if __name__ == "__main__":
    main()
