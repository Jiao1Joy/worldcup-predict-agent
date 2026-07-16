import { useState } from 'react';

export function App() {
  const [showWorkbench, setShowWorkbench] = useState(false);
  return (
    <main>
      <h1>World Cup Prediction Agent</h1>
      {showWorkbench ? (
        <section aria-label="Agent Workbench">Workbench loading…</section>
      ) : (
        <button type="button" onClick={() => setShowWorkbench(true)}>
          View Agent Run
        </button>
      )}
    </main>
  );
}
