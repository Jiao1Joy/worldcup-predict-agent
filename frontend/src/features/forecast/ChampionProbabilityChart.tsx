import ReactECharts from 'echarts-for-react';
import type { TournamentForecast } from '../../domain/forecast';
import { sortedTeamProbabilities } from '../../domain/forecast';

export function ChampionProbabilityChart({ forecast }: { forecast: TournamentForecast }) {
  const sorted = sortedTeamProbabilities(forecast).slice(0, 10);
  const option = {
    aria: { enabled: true, decal: { show: true } },
    title: { text: 'Top 10 champion probabilities', left: 'center', textStyle: { color: '#e7edf7' } },
    tooltip: { trigger: 'axis' },
    grid: { left: '15%', right: '10%' },
    xAxis: { type: 'value', max: 1, axisLabel: { color: '#8ea0b8', formatter: (v: number) => `${(v * 100).toFixed(0)}%` } },
    yAxis: { type: 'category', data: sorted.map((s) => s.team).reverse(), axisLabel: { color: '#8ea0b8' } },
    series: [
      {
        type: 'bar',
        data: sorted.map((s) => s.champion).reverse(),
        itemStyle: { color: '#68d8c5' },
        label: { show: true, formatter: (p: { value: number }) => `${(p.value * 100).toFixed(1)}%`, color: '#e7edf7' },
      },
    ],
  };
  return (
    <section className="chart-card" aria-label="Champion probability chart" aria-description="Horizontal bar chart of the top ten champion probabilities">
      <ReactECharts option={option} style={{ height: 360 }} />
    </section>
  );
}
