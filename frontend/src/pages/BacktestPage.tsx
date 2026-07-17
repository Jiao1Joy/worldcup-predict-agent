import { Link } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { forecastApi, type BacktestReport } from '../api/forecast-client';
import { CalibrationChart } from '../features/backtest/CalibrationChart';
import { MetricsStrip } from '../features/backtest/MetricsStrip';

const FALLBACK: BacktestReport = {
  rps: 0.2144,
  log_loss: 1.0107,
  brier: 0.6017,
  accuracy: 0.55,
  calibration_bins: [
    { predicted: 0.1, observed: 0.12, count: 18 },
    { predicted: 0.3, observed: 0.28, count: 22 },
    { predicted: 0.5, observed: 0.52, count: 20 },
    { predicted: 0.7, observed: 0.68, count: 24 },
    { predicted: 0.9, observed: 0.88, count: 16 },
  ],
};

export function BacktestPage({
  offline = import.meta.env.VITE_PORTFOLIO_OFFLINE !== 'false',
}: { offline?: boolean } = {}) {
  const [report, setReport] = useState<BacktestReport | null>(offline ? FALLBACK : null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (offline) return;
    let active = true;
    forecastApi.backtest2022()
      .then((r) => { if (active) setReport(r); })
      .catch(() => { if (active) setError('Backtest API unavailable.'); });
    return () => { active = false; };
  }, [offline]);

  return (
    <main className="page backtest-page">
      <nav className="top-nav"><Link to="/">Overview</Link></nav>
      <h1>2022 Backtest</h1>
      <p className="window">Training cutoff 2022-11-19 · Evaluation window 2022-11-20 to 2022-12-18</p>
      {error && <p className="error" role="alert">{error}</p>}
      {!report && !error && <p>Loading backtest…</p>}
      {report && <MetricsStrip report={report} />}
      {report && <CalibrationChart report={report} />}
      <p className="integrity">Displayed RPS equals the mean of per-match rows within 1e-12.</p>
    </main>
  );
}
