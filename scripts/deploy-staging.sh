#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${1:-.env.staging}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing env file: $ENV_FILE"
  echo "Copy .env.production.example and customize secrets."
  exit 1
fi

export APP_VERSION="$(tr -d ' \n\r' < VERSION)"

echo "==> Deploying Expense Tracker API ($APP_VERSION) with $ENV_FILE"
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file "$ENV_FILE" pull --ignore-buildable || true
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file "$ENV_FILE" build
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file "$ENV_FILE" up -d postgres redis
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file "$ENV_FILE" run --rm api alembic upgrade head
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file "$ENV_FILE" up -d

echo "==> Waiting for readiness"
for _ in $(seq 1 30); do
  if curl -sf http://localhost/api/v1/health/ready >/dev/null 2>&1; then
    echo "API ready"
    exit 0
  fi
  sleep 5
done

echo "Readiness check failed — inspect logs: docker compose logs api"
exit 1
