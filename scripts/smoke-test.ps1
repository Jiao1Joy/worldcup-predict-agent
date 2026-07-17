$ErrorActionPreference = "Stop"
$health = Invoke-RestMethod http://127.0.0.1:4173/api/health
if ($health.status -ne "ok") { throw "Backend health check failed" }
$page = Invoke-WebRequest http://127.0.0.1:4173/
if ($page.StatusCode -ne 200) { throw "Frontend did not return 200" }
Write-Host "Smoke test passed"
