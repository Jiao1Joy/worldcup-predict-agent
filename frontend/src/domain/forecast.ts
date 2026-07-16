export interface StageProbabilities {
  r32: number;
  r16: number;
  qf: number;
  sf: number;
  final: number;
  champion: number;
}

export interface MatchPrediction {
  match_id: string;
  home_team: string;
  away_team: string;
  expected_home_goals: number;
  expected_away_goals: number;
  outcomes: { home: number; draw: number; away: number };
  score_matrix: number[][];
  evidence_ids: string[];
}

export interface ForecastMatch {
  match_id: string;
  stage: string;
  home_source: string;
  away_source: string;
  home_team: string | null;
  away_team: string | null;
  prediction: MatchPrediction | null;
  winner: string | null;
}

export interface TournamentForecast {
  forecast_id: string;
  run_id: string;
  champion: { team: string; probability: number };
  matches: ForecastMatch[];
  team_probabilities: Record<string, StageProbabilities>;
  simulation_runs: number;
  seed: number;
  versions: Record<string, string>;
  evidence_ids: string[];
  explanation: { summary: string; uncertainty: string };
}

export function assertTournamentForecast(value: unknown): asserts value is TournamentForecast {
  if (!value || typeof value !== 'object') throw new Error('forecast must be an object');
  const forecast = value as Partial<TournamentForecast>;
  if (typeof forecast.forecast_id !== 'string') throw new Error('forecast_id is required');
  if (!Array.isArray(forecast.matches) || forecast.matches.length !== 104) throw new Error('forecast requires 104 matches');
  if (!forecast.team_probabilities || Object.keys(forecast.team_probabilities).length !== 48) throw new Error('forecast requires 48 teams');
  if (!forecast.champion || typeof forecast.champion.probability !== 'number') throw new Error('champion is required');
}

export function sortedTeamProbabilities(forecast: TournamentForecast) {
  return Object.entries(forecast.team_probabilities)
    .map(([team, probs]) => ({ team, ...probs }))
    .sort((a, b) => b.champion - a.champion);
}
