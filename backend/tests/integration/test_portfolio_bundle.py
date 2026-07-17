import json
from pathlib import Path

ROOT = Path(__file__).parents[3] / "artifacts" / "demo"


def test_committed_portfolio_bundle_is_complete_and_self_consistent() -> None:
    forecast = json.loads((ROOT / "forecast.json").read_text(encoding="utf-8"))
    run = json.loads((ROOT / "completed-run.json").read_text(encoding="utf-8"))
    evidence = json.loads((ROOT / "evidence.json").read_text(encoding="utf-8"))

    assert len(forecast["matches"]) == 104
    assert len(forecast["team_probabilities"]) == 48
    assert forecast["run_id"] == run["state"]["run_id"]
    assert set(forecast["evidence_ids"]) <= {item["evidence_id"] for item in evidence}
