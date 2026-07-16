import fixture from './fixtures/forecast.json';
import type { TournamentForecast } from '../domain/forecast';

const forecast = fixture as TournamentForecast;

// The tournament forecast stores knockout outcomes; for the match-detail
// product surface we attach an example prediction to the first resolved match
// so the score-matrix view has data to render. Values are illustrative and
// labelled as fixture provenance.
const SAMPLE_MATRIX = [
  [0.08, 0.07, 0.05, 0.03, 0.01, 0.0, 0.0, 0.0, 0.0],
  [0.10, 0.09, 0.06, 0.03, 0.01, 0.0, 0.0, 0.0, 0.0],
  [0.07, 0.08, 0.06, 0.03, 0.01, 0.0, 0.0, 0.0, 0.0],
  [0.04, 0.05, 0.04, 0.02, 0.01, 0.0, 0.0, 0.0, 0.0],
  [0.02, 0.02, 0.02, 0.01, 0.0, 0.0, 0.0, 0.0, 0.0],
  [0.01, 0.01, 0.01, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
  [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
  [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
  [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
];
const firstPredicted = forecast.matches.find((m) => m.home_team && m.away_team);
if (firstPredicted) {
  firstPredicted.prediction = {
    match_id: firstPredicted.match_id,
    home_team: firstPredicted.home_team!,
    away_team: firstPredicted.away_team!,
    expected_home_goals: 1.3,
    expected_away_goals: 0.9,
    outcomes: { home: 0.45, draw: 0.28, away: 0.27 },
    score_matrix: SAMPLE_MATRIX,
    evidence_ids: [`MATCH-${firstPredicted.match_id}-PRED`],
  };
}

export const forecastFixture = forecast;
