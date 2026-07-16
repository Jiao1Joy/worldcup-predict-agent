import csv
from itertools import combinations
from pathlib import Path


class AnnexC:
    SLOT_COLUMNS = ("slot_1A", "slot_1B", "slot_1D", "slot_1E", "slot_1G", "slot_1I", "slot_1K", "slot_1L")

    def __init__(self, combinations_by_key: dict[str, dict[str, str]]) -> None:
        self.combinations = combinations_by_key

    @classmethod
    def load(cls, path: Path):
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        mapping = {
            row["qualified_groups"]: {column.removeprefix("slot_"): row[column] for column in cls.SLOT_COLUMNS}
            for row in rows
        }
        expected = {"".join(value) for value in combinations("ABCDEFGHIJKL", 8)}
        if set(mapping) != expected:
            raise ValueError("Annexe C must cover all 495 combinations")
        for key, slots in mapping.items():
            if sorted(slots.values()) != sorted(key):
                raise ValueError(f"Annexe C mapping is invalid for {key}")
        return cls(mapping)

    def resolve(self, qualified_groups: set[str]) -> dict[str, str]:
        return self.combinations["".join(sorted(qualified_groups))]
