from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def serialize_report(
    metrics: dict[str, Any],
    per_match: list[dict[str, Any]],
    output_stem: str,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    if not per_match:
        raise ValueError("backtest report requires per-match rows")

    report = {"aggregate": metrics, "per_match": per_match}

    if output_dir is not None:
        directory = Path(output_dir)
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"{output_stem}.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        lines = [
            "match_id,date,home_team,away_team,home_score,away_score,outcome,"
            "home_probability,draw_probability,away_probability,predicted_outcome,rps"
        ]
        for row in per_match:
            lines.append(
                f"{row['match_id']},{row['date']},{row['home_team']},{row['away_team']},"
                f"{row['home_score']},{row['away_score']},{row['outcome']},"
                f"{row['home_probability']},{row['draw_probability']},{row['away_probability']},"
                f"{row['predicted_outcome']},{row['rps']}"
            )
        (directory / f"{output_stem}-predictions.csv").write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )

    return report
