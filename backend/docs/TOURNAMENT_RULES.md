# FIFA 2026 Tournament Rules

## Format

- 48 teams in 12 groups (A-L) of 4.
- Group stage: each group plays 6 round-robin matches (72 total, M001-M072).
- Top 2 from each group plus 8 best third-placed teams advance to Round of 32 (32 teams).
- Knockout: R32 (16), R16 (8), QF (4), SF (2), 3rd place (1), Final (1) = 32 matches.
- Total: 72 + 32 = 104 matches.

## Group ranking criteria

1. Points
2. Head-to-head (points, goal difference, goals) among tied teams
3. Overall goal difference
4. Overall goals scored
5. Fair-play score
6. FIFA ranking (ascending)

The tie-breaker recursively re-applies the head-to-head mini-table to any still-tied subset after a partial split.

## Best third-placed teams

The 8 best thirds are ranked by points, goal difference, goals scored, fair-play, and FIFA ranking. Their assignment to R32 bracket slots is governed by **Annexe C** (495 combinations of C(12,8)).

## Annexe C

- Source: FIFA World Cup 26 Regulations, Annexe C (PDF pages 80-97).
- Source SHA-256: recorded in `rules-manifest.json`.
- The table maps each possible set of 8 qualifying third-placed groups to their R32 slot assignments.
- Coverage: 495/495 combinations, validated at load time.

## Fixtures

`fixtures.json` defines the 104 match slots (M001-M104) and their bracket sources:
- Group stage: `G{group}{seed}` (e.g. `GA1` = group A seed 1).
- R32: `1{group}` (winner), `2{group}` (runner-up), `3` (best-third via Annexe C).
- Later rounds: `W{match_id}` (winner), `L{match_id}` (loser of a semifinal).

## Knockout resolution

Draws in knockout matches go to extra time (reduced-intensity Poisson); if still level, penalties at a configurable probability (default 0.5). Sampled draws are never overridden by Elo.

## Reproducibility

Fixed seed and identical rules/artifacts produce an identical canonical hash. Batch seeds derive from `numpy.random.SeedSequence([root_seed, batch_index])`.
