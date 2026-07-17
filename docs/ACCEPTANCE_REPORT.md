# Acceptance Report

Updated: 2026-07-17
Scope: local Portfolio application and its reproducible baseline artifacts

All criteria below were executed against the actual repository state. `PASS` means the command ran and succeeded; `NOT RUN` means an optional profile that was not executed locally.

## Domain invariants

| Criterion | Status | Evidence |
| --- | --- | --- |
| No post-cutoff data enters frozen forecast | PASS | `tests/unit/data/test_snapshot.py` excludes rows after cutoff |
| Score matrices non-negative and normalized | PASS | `tests/unit/prediction/test_goal_models.py` |
| Fused outcomes match score-matrix regions within 1e-9 | PASS | `tests/integration/test_match_prediction_service.py::test_score_matrix_regions_match_fused_outcomes` |
| Artifact hashes reject data-version mismatch | PASS | `tests/integration/test_artifact_roundtrip.py::test_repository_rejects_mismatched_data_version` |
| Annexe C covers 495/495 combinations | PASS | `tests/unit/tournament/test_annex_c.py::test_annex_c_covers_every_eight_group_combination` |
| Each tournament run has 104 matches, one champion | PASS | `tests/unit/tournament/test_full_tournament.py::test_one_run_plays_all_104_matches_and_one_champion` |
| Fixed seed reproduces identical run hash | PASS | `tests/unit/tournament/test_full_tournament.py::test_fixed_seed_produces_identical_run_hash` |
| Champion probabilities sum to 1 | PASS | `tests/integration/test_tournament_forecast.py::test_forecast_probabilities_and_batches_are_reproducible` |
| Backtest aggregate RPS recomputable from per-match rows (1e-12) | PASS | `tests/integration/test_2022_backtest.py::test_backtest_metrics_recomputed_from_per_match_rows` |

## Agent invariants

| Criterion | Status | Evidence |
| --- | --- | --- |
| No-key mode completes a real 104-match forecast | PASS | `tests/integration/test_llm_fallback.py` |
| Product API does not call demo registry | PASS | `worldcup_agent/api/dependencies.py` uses `build_production_registry` in production mode |
| Tool Registry is the only path to domain services | PASS | `tests/integration/test_real_tool_run.py` |
| Published numeric claims have evidence coverage | PASS | `tests/integration/test_evidence_publish.py` |
| Replay performs zero external calls | PASS | `tests/integration/test_replay.py` (state rebuilt from events) |
| Timeout recovery preserves completed state | PASS | `tests/integration/test_checkpoint_recovery.py::test_timeout_recovers_from_checkpoint_without_losing_state` |
| Human approval pauses and resumes | PASS | `tests/integration/test_checkpoint_recovery.py::test_conflicting_snapshot_pauses_for_human_and_resumes` |

## Test gates

| Gate | Status | Command |
| --- | --- | --- |
| Backend pytest | PASS | `cd backend && python -m pytest -q` → 86 passed |
| Backend ruff | PASS | `cd backend && python -m ruff check src tests` → All checks passed |
| Frontend vitest | PASS | `cd frontend && npm test` → 25 passed |
| Frontend build | PASS | `cd frontend && npm run build` → built |
| Frontend Playwright | PASS | `cd frontend && npm run e2e` → 4 passed |
| Portfolio bundle integrity | PASS | `tests/integration/test_portfolio_bundle.py` |
| Rebuild from public data | PASS | `worldcup-rebuild --source ../international_results-master/results.csv ...` produced artifacts (RPS 0.2144 on 100 eval matches) |

## Product journeys

| Journey | Status | Evidence |
| --- | --- | --- |
| Overview → Tournament → Match → Agent | PASS | `e2e/forecast-product.spec.ts::visitor moves from champion result...` |
| Mobile 390px no horizontal overflow | PASS | `e2e/forecast-product.spec.ts::mobile product has no page-level horizontal overflow` |
| Runtime forecast → Visual Explorer | PASS | `/explore` derives probabilities, groups, Annexe C and knockout paths from the supplied `TournamentForecast` |
| Workbench inspect + replay | PASS | `e2e/portfolio-demo.spec.ts::portfolio visitor can inspect and replay...` |
| Offline portfolio requires no backend | PASS | fixture-backed `App` and `forecast-fixture.ts` |

## Explicitly excluded scope

| Item | Status | Reason |
| --- | --- | --- |
| Full GBDT training | OUT OF SCOPE | The reproducible baseline model is the product profile; no full-training run is required |
| Public deployment | OUT OF SCOPE | The deliverable is a local Portfolio application |
| Docker runtime/build verification | OUT OF SCOPE | Docker is not required by the project owner |

## Documentation

| Document | Status |
| --- | --- |
| README with quick start, commands, versions | PASS |
| DATA_SOURCES with license/attribution | PASS |
| SECURITY with redaction/secrets | PASS |
| ARCHITECTURE with dependency direction | PASS |
| DEMO_SCRIPT (six-minute) | PASS |
| LLM_AGENT / PREDICTION_ENGINE / TOURNAMENT_RULES | PASS |

## Optional integration profile

| Profile | Status | Reason |
| --- | --- | --- |
| Live LLM run | NOT RUN | Requires an API key; deterministic fallback path is verified and is the default |

## Conclusion

All required local Portfolio criteria are PASS. Full training, public deployment and Docker verification are intentionally excluded by the project owner. The live LLM profile remains optional; the default deterministic fallback is verified. The project is complete within this documented scope.
