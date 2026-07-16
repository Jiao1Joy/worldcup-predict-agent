from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BatchResult:
    batch_index: int
    seed_entropy: list[int]
    runs: int
    stage_counts: dict[str, dict[str, int]] = field(default_factory=dict)
    champion_counts: dict[str, int] = field(default_factory=dict)
    content_hash: str = ""


@dataclass
class ConvergenceRecord:
    batches: list[BatchResult] = field(default_factory=list)
    deltas: list[float] = field(default_factory=list)

    @property
    def total_runs(self) -> int:
        return sum(b.runs for b in self.batches)

    @property
    def is_converged(self) -> bool:
        if self.total_runs < 10_000 or len(self.deltas) < 3:
            return False
        return all(delta < 0.005 for delta in self.deltas[-3:])

    @property
    def latest_delta(self) -> float:
        return self.deltas[-1] if self.deltas else 1.0
