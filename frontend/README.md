# Agent Workbench

Offline portfolio mode uses the committed completed-run fixture:

```powershell
npm install
npm run dev
```

Live mode connects to a backend run:

```powershell
$env:VITE_DEMO_RUN_ID="wc26-demo-run"
npm run dev
```

The interview path is: result summary → Run Graph → Step Inspector → dynamic branch → failure recovery → Evidence → Replay.

## Verification

```powershell
npm test        # Vitest unit/component tests
npm run build   # TypeScript + Vite production build
npm run e2e     # Playwright portfolio + mobile journeys
```
