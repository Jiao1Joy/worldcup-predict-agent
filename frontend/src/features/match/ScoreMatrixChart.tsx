import ReactECharts from 'echarts-for-react';

export function ScoreMatrixChart({ matrix, homeTeam, awayTeam }: { matrix: number[][]; homeTeam: string; awayTeam: string }) {
  const size = matrix.length;
  const data: [number, number, number][] = [];
  for (let i = 0; i < size; i++) {
    for (let j = 0; j < size; j++) {
      data.push([j, i, matrix[i][j]]);
    }
  }
  const option = {
    aria: { enabled: true, decal: { show: true } },
    tooltip: { formatter: (p: { value: [number, number, number] }) => `${awayTeam} ${p.value[0]} - ${homeTeam} ${p.value[1]}: ${(p.value[2] * 100).toFixed(1)}%` },
    grid: { left: '12%', right: '5%', bottom: '15%' },
    xAxis: { type: 'category', name: awayTeam, data: Array.from({ length: size }, (_, i) => i), axisLabel: { color: '#8ea0b8' } },
    yAxis: { type: 'category', name: homeTeam, data: Array.from({ length: size }, (_, i) => i), axisLabel: { color: '#8ea0b8' } },
    visualMap: { min: 0, max: 0.3, calculable: true, orient: 'horizontal', left: 'center', bottom: '0%', textStyle: { color: '#8ea0b8' } },
    series: [{ type: 'heatmap', data, label: { show: true, formatter: (p: { value: [number, number, number] }) => `${(p.value[2] * 100).toFixed(1)}` } }],
  };
  return (
    <section aria-label="Score probability matrix" aria-description={`Heatmap of score probabilities for ${homeTeam} vs ${awayTeam}`}>
      <ReactECharts option={option} style={{ height: 360 }} />
      <table className="sr-only">
        <caption>Score probability matrix</caption>
        <tbody>
          {matrix.map((row, i) => (
            <tr key={i}>{row.map((c, j) => <td key={j}>{c.toFixed(4)}</td>)}</tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
