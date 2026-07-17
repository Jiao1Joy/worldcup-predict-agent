# FIFA World Cup 26 rule data

## Final groups

- Primary source: [World Cup 2026 groups: How teams qualify and tie-breakers](https://www.fifa.com/en/articles/groups-how-teams-qualify-tie-breakers)
- Cross-check: [Official FIFA World Cup 2026 match schedule, fixtures and results](https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/match-schedule-fixtures-results-teams-stadiums)
- Source publisher: FIFA
- Source state: all 48 teams confirmed after the UEFA and FIFA Play-Off Tournaments
- Retrieved: 2026-07-16
- Generated file: `groups.json`
- JSON SHA-256: `5d791712c34609f1ae9495bce9242a95f6a620a95f5a404581d7e637d9e62bbc`

`groups.json` contains groups A-L in draw position order, with four unique
canonical `team_id` values per group. The IDs use the names found in the
project's historical international-results dataset so that rule data joins
directly to model input data. The following FIFA display names are normalized:

| FIFA display name | Canonical team ID |
| --- | --- |
| USA | United States |
| Korea Republic | South Korea |
| Czechia | Czech Republic |
| Türkiye | Turkey |
| Côte d'Ivoire | Ivory Coast |
| IR Iran | Iran |
| Cabo Verde | Cape Verde |
| Congo DR | DR Congo |

Validation requires exactly 12 keys (`A` through `L`), four teams per group,
48 globally unique team IDs, and a match for every ID in the historical
results dataset. All checks passed on 2026-07-16.

## Match graph and FIFA rankings

`fixtures.json` versions all M001-M104 source slots. In particular, M073-M088
use the official round-of-32 graph and each `3` placeholder is resolved against
the named group-winner slot in Annexe C; mappings are never consumed by row
order. `fifa_rankings.json` stores the official men's ranking snapshot dated
2026-06-11 and must cover exactly the same 48 canonical team IDs as
`groups.json`. Both files are SHA-256 checked by `rules-manifest.json` at load.

## Annexe C

- Source: [Regulations for the FIFA World Cup 26](https://digitalhub.fifa.com/m/636f5c9c6f29771f/original/FWC2026_regulations_EN.pdf)
- Source publisher: FIFA
- Source edition: May 2026, English
- Retrieved: 2026-07-16
- Source location: Annexe C, physical PDF pages 80-97
- Source PDF SHA-256: `bad4ea83cf1f51055598b0c12c3dab280a78777e08a623b9e9098508b4ecc8d9`
- Generated file: `annex_c.csv`
- CSV SHA-256: `b8aa41ee9660bc0703e127942f1a3beaae8c2ce3e602bbc43fa76b3b16475553`

The source table's columns `1A`, `1B`, `1D`, `1E`, `1G`, `1I`, `1K`, and
`1L` identify the group-winner slots in the round of 32. Values such as `3E`
identify the third-placed team from that group. The canonical CSV removes the
constant `3` prefix and names the columns `slot_1A` through `slot_1L`.

`qualified_groups` is the sorted set of the eight third-place group letters in
the source row. It is derived directly from the eight slot values, not from a
separately inferred pairing rule.

## Extraction and validation

The table was extracted with `scripts/extract_fifa_annex_c.py` using
`pypdf==6.1.1`. The extractor reads options 1-495 from the official PDF and
fails unless all of the following hold:

- options 1 through 495 are present exactly once;
- every row contains eight distinct groups from A through L;
- all 495 `qualified_groups` keys are unique;
- the keys exactly equal every eight-group combination from A through L;
- every row maps its eight qualified groups to the eight winner slots once.

The generated CSV was independently re-read with Python's standard `csv`
module and checked against `itertools.combinations("ABCDEFGHIJKL", 8)`.
Options 1 and 495 were also spot-checked against the source PDF. Review and
generation performed by Codex on 2026-07-16.

Rebuild command:

```powershell
python -m pip install pypdf==6.1.1
python scripts/extract_fifa_annex_c.py `
  FWC2026_regulations_EN.pdf `
  backend/rules/fifa_2026/annex_c.csv
```
