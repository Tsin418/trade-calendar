#!/usr/bin/env bash
set -Eeuo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "${script_dir}/.." && pwd)"
cd "${repo_root}"

compose=(docker compose --file infrastructure/docker-compose.yml)

if [[ ! -f .env ]]; then
  echo "Missing .env. Copy infrastructure/oci.env.example to .env and fill the secrets." >&2
  exit 1
fi

if ! grep -Eq '^CALENDAR_ENVIRONMENT=production[[:space:]]*$' .env; then
  echo "Refusing to deploy: .env must contain CALENDAR_ENVIRONMENT=production." >&2
  exit 1
fi

mkdir -p backups

if "${compose[@]}" ps --status running --services | grep -qx db; then
  timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
  backup_path="backups/calendar-${timestamp}.dump"
  echo "Backing up PostgreSQL to ${backup_path}"
  "${compose[@]}" exec -T db sh -c \
    'pg_dump --format=custom --username="$POSTGRES_USER" --dbname="$POSTGRES_DB"' \
    > "${backup_path}"
fi

echo "Building ARM64-compatible application images"
"${compose[@]}" build migrate api worker

echo "Starting PostgreSQL"
"${compose[@]}" up -d db

for attempt in $(seq 1 30); do
  if "${compose[@]}" exec -T db sh -c \
    'pg_isready --username="$POSTGRES_USER" --dbname="$POSTGRES_DB"' >/dev/null 2>&1; then
    break
  fi
  if [[ "${attempt}" -eq 30 ]]; then
    echo "PostgreSQL did not become ready." >&2
    exit 1
  fi
  sleep 2
done

echo "Applying database migrations"
"${compose[@]}" run --rm migrate

echo "Starting API and scheduler worker"
"${compose[@]}" up -d --no-deps api worker

for attempt in $(seq 1 30); do
  if curl --fail --silent --show-error http://127.0.0.1:8000/ready >/dev/null; then
    break
  fi
  if [[ "${attempt}" -eq 30 ]]; then
    echo "API readiness check failed." >&2
    "${compose[@]}" logs --tail=100 api
    exit 1
  fi
  sleep 2
done

"${compose[@]}" ps

if command -v systemctl >/dev/null 2>&1 && ! systemctl is-active --quiet cloudflared; then
  echo "WARNING: cloudflared is not active; the public calendar cannot reach this API yet." >&2
fi

echo "OCI backend deployment is healthy."
