import { assertTournamentForecast, type TournamentForecast } from '../domain/forecast';

async function parseForecast(response: Response): Promise<TournamentForecast> {
  if (!response.ok) throw new Error(`forecast request failed: ${response.status}`);
  const value: unknown = await response.json();
  assertTournamentForecast(value);
  return value;
}

export interface BacktestReport {
  rps: number;
  log_loss: number;
  brier: number;
  accuracy: number;
  calibration_bins: Array<{ predicted: number; observed: number; count: number }>;
}

export const forecastApi = {
  current: () => fetch('/api/forecasts/current').then(parseForecast),
  get: (forecastId: string) => fetch(`/api/forecasts/${forecastId}`).then(parseForecast),
  backtest2022: async () => {
    const response = await fetch('/api/backtests/2022');
    if (!response.ok) throw new Error(`backtest request failed: ${response.status}`);
    return response.json() as Promise<BacktestReport>;
  },
};
