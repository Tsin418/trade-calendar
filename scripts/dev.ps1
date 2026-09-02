$ErrorActionPreference = "Stop"
$composeFile = Join-Path $PSScriptRoot "..\infrastructure\docker-compose.yml"
docker compose --file $composeFile up --build

