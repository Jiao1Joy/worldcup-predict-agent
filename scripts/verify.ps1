$ErrorActionPreference = "Stop"
Push-Location backend
try {
  python -m pytest -q
  python -m ruff check src tests
} finally { Pop-Location }
Push-Location frontend
try {
  npm ci
  npm test
  npm run build
  npm run e2e
} finally { Pop-Location }
Write-Host "All verification gates passed"
