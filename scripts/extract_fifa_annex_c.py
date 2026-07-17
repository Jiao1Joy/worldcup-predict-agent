"""Extract FIFA World Cup 26 Annexe C into the project's canonical CSV."""

from __future__ import annotations

import argparse
import csv
import re
from itertools import combinations
from pathlib import Path

from pypdf import PdfReader


SLOT_COLUMNS = (
    "slot_1A",
    "slot_1B",
    "slot_1D",
    "slot_1E",
    "slot_1G",
    "slot_1I",
    "slot_1K",
    "slot_1L",
)
ROW_PATTERN = re.compile(
    r"^\s*(?P<option>\d{1,3})\s+"
    r"(?P<slots>3[A-L](?:\s+3[A-L]){7})\s*$"
)


def extract_rows(pdf_path: Path) -> list[dict[str, str]]:
    reader = PdfReader(pdf_path)
    if len(reader.pages) < 97:
        raise ValueError(f"Expected at least 97 PDF pages, found {len(reader.pages)}")

    extracted: dict[int, list[str]] = {}
    # Annexe C is on physical PDF pages 80-97 (zero-based indexes 79-96).
    for page in reader.pages[79:97]:
        for line in (page.extract_text() or "").splitlines():
            match = ROW_PATTERN.fullmatch(line)
            if match is None:
                continue
            option = int(match.group("option"))
            if option in extracted:
                raise ValueError(f"Duplicate Annexe C option {option}")
            extracted[option] = match.group("slots").split()

    expected_options = set(range(1, 496))
    if set(extracted) != expected_options:
        missing = sorted(expected_options - set(extracted))
        extra = sorted(set(extracted) - expected_options)
        raise ValueError(f"Expected options 1-495; missing={missing}, extra={extra}")

    rows: list[dict[str, str]] = []
    seen_combinations: set[str] = set()
    for option in range(1, 496):
        groups = [slot.removeprefix("3") for slot in extracted[option]]
        if len(set(groups)) != 8:
            raise ValueError(f"Option {option} does not contain eight unique groups")
        qualified_groups = "".join(sorted(groups))
        if qualified_groups in seen_combinations:
            raise ValueError(f"Duplicate qualified-group combination {qualified_groups}")
        seen_combinations.add(qualified_groups)
        rows.append(
            {
                "qualified_groups": qualified_groups,
                **dict(zip(SLOT_COLUMNS, groups, strict=True)),
            }
        )

    expected_combinations = {
        "".join(group_set) for group_set in combinations("ABCDEFGHIJKL", 8)
    }
    if seen_combinations != expected_combinations:
        missing = sorted(expected_combinations - seen_combinations)
        extra = sorted(seen_combinations - expected_combinations)
        raise ValueError(
            f"Annexe C does not cover all C(12, 8) combinations; "
            f"missing={missing}, extra={extra}"
        )
    return rows


def write_csv(rows: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=("qualified_groups", *SLOT_COLUMNS),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path, help="FIFA World Cup 26 regulations PDF")
    parser.add_argument("output", type=Path, help="Destination annex_c.csv")
    args = parser.parse_args()

    rows = extract_rows(args.pdf)
    write_csv(rows, args.output)
    print(f"Wrote {len(rows)} validated rows to {args.output}")


if __name__ == "__main__":
    main()
