import type { BacktestReport } from '../../api/forecast-client';

export function MetricsStrip({ report }: { report: BacktestReport }) {
  return (
    <section className="metrics-strip" aria-label="Backtest metrics">
      <div><strong>RPS</strong><span>{report.rps.toFixed(4)}</span><small>primary</small></div>
      <div><strong>Log Loss</strong><span>{report.log_loss.toFixed(4)}</span></div>
      <div><strong>Brier</strong><span>{report.brier.toFixed(4)}</span></div>
      <div><strong>Accuracy</strong><span>{(report.accuracy * 100).toFixed(1)}%</span><small>secondary</small></div>
    </section>
  );
}
