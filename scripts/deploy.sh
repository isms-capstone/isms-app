#!/usr/bin/env bash
set -euo pipefail

environment="${1:?Usage: deploy.sh staging|prod expected-commit}"
expected_commit="${2:?An exact expected commit is required}"
case "$environment" in staging|prod) ;; *) echo "Unsupported environment" >&2; exit 1 ;; esac
cd "$(dirname "$0")/.."
if [[ "$(git rev-parse HEAD)" != "$expected_commit" ]]; then
  echo "Checkout differs from the approved workflow commit; deployment stopped." >&2
  exit 1
fi
env_file=".env.$environment"
if [[ ! -f "$env_file" ]]; then
  echo "Missing $env_file; configure the server environment before deployment." >&2
  exit 1
fi
compose=(docker compose --env-file "$env_file" -p "isms-$environment" -f docker-compose.yml -f "docker-compose.$environment.yml")
"${compose[@]}" config --quiet
"${compose[@]}" build app
"${compose[@]}" up -d --wait --wait-timeout 120 db
# Preflight is read-only. Never automatically stamp an existing unmanaged schema.
"${compose[@]}" run --rm --no-deps app python -m app.db.migration_state
"${compose[@]}" run --rm --no-deps app python -m alembic upgrade head
# A failed preflight/migration stops before replacing the application container.
"${compose[@]}" up -d --no-deps --wait --wait-timeout 120 app
