from datetime import UTC, datetime

import pandas as pd

from worldcup_agent.data.snapshot import build_snapshot


def test_snapshot_normalizes_aliases_and_excludes_future_rows(tmp_path) -> None:
    source = tmp_path / "results.csv"
    pd.DataFrame(
        [
            {"date": "2022-11-18", "home_team": "USA", "away_team": "IR Iran", "home_score": 1, "away_score": 0, "tournament": "Friendly", "city": "A", "country": "B", "neutral": True},
            {"date": "2022-11-21", "home_team": "United States", "away_team": "Iran", "home_score": 2, "away_score": 0, "tournament": "World Cup", "city": "C", "country": "D", "neutral": True},
        ]
    ).to_csv(source, index=False)

    frame, manifest = build_snapshot(
        source,
        tmp_path / "snapshot.parquet",
        cutoff=datetime(2022, 11, 19, 23, 59, 59, tzinfo=UTC),
        source_uri="fixture://results.csv",
    )

    assert len(frame) == 1
    assert frame.iloc[0]["home_team"] == "United States"
    assert frame.iloc[0]["away_team"] == "Iran"
    assert manifest.row_count == 1
    assert len(manifest.source_sha256) == 64
