$ErrorActionPreference = "Stop"
docker compose up -d --build
& "$PSScriptRoot\smoke-test.ps1"
Write-Host "World Cup Prediction Agent: http://127.0.0.1:4173"
