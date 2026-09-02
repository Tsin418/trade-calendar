$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..")

Push-Location (Join-Path $root "apps\api")
try {
    .\.venv\Scripts\ruff.exe check --no-cache trade_calendar tests ..\worker
    .\.venv\Scripts\mypy.exe trade_calendar ..\worker
    .\.venv\Scripts\pytest.exe -q
} finally {
    Pop-Location
}

Push-Location (Join-Path $root "apps\web")
try {
    npm run lint
    npm run typecheck
    npm run test
    npm run test:e2e
    npm run build
} finally {
    Pop-Location
}
