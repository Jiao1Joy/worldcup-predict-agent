import hashlib
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from worldcup_agent.data.contracts import DataSnapshotManifest
from worldcup_agent.data.normalize import normalize_matches


def build_snapshot(source: Path, output: Path, cutoff: datetime, source_uri: str):
    source_bytes = source.read_bytes()
    frame = normalize_matches(pd.read_csv(source))
    frame = frame[frame["date"] <= cutoff].copy()
    if frame.empty:
        raise ValueError("snapshot contains no matches before cutoff")
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(output, index=False)
    digest = hashlib.sha256(source_bytes).hexdigest()
    manifest = DataSnapshotManifest(
        data_version=f"matches-{cutoff:%Y%m%d}-{digest[:12]}",
        source_name="martj42-international-results",
        source_uri=source_uri,
        source_sha256=digest,
        snapshot_cutoff=cutoff,
        row_count=len(frame),
    )
    output.with_suffix(".manifest.json").write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2), encoding="utf-8"
    )
    return frame, manifest
