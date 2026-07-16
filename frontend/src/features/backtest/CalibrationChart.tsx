import ReactECharts from 'echarts-for-react';
import type { BacktestReport } from '../../api/forecast-client';

export function CalibrationChart({ report }: { report: BacktestReport }) {
  const bins = report.calibration_bins;
  const option = {
    aria: { enabled: true, decal: { show: true } },
    title: { text: 'Calibration', left: 'center', textStyle: { color: '#e7edf7' } },
    xAxis: { type: 'value', min: 0, max: 1, name: 'predicted', axisLabel: { color: '#8ea0b8' } },
    yAxis: { type: 'value', min: 0, max: 1, name: 'observed', axisLabel: { color: '#8ea0b8' } },
    series: [
      { type: 'line', data: [[0, 0], [1, 1]], lineStyle: { type: 'dashed', color: '#8ea0b8' }, showSymbol: false, name: 'perfect' },
      { type: 'scatter', data: bins.map((b) => [b.predicted, b.observed]), symbolSize: 10, itemStyle: { color: '#68d8c5' }, name: 'observed' },
    ],
  };
  return (
    <section aria-label="Calibration chart" aria-description="Predicted vs observed probabilities with a perfect-calibration diagonal">
      <ReactECharts option={option} style={{ height: 320 }} />
      <table>
        <caption>Calibration bins</caption>
        <thead><tr><th>Predicted</th><th>Observed</th><th>Count</th></tr></thead>
        <tbody>{bins.map((b, i) => <tr key={i}><td>{b.predicted.toFixed(3)}</td><td>{b.observed.toFixed(3)}</td><td>{b.count}</td></tr>)}</tbody>
      </table>
    </section>
  );
}
