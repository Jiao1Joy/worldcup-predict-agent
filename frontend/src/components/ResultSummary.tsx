export function ResultSummary({ onOpenWorkbench }: { onOpenWorkbench: () => void }) {
  return (
    <main className="result-summary">
      <p className="eyebrow">2026 TOURNAMENT FORECAST</p>
      <h1>World Cup Prediction Agent</h1>
      <p>The result is a probability distribution backed by a replayable Agent run.</p>
      <button type="button" onClick={onOpenWorkbench}>View Agent Run</button>
    </main>
  );
}
