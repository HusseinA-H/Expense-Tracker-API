#!/usr/bin/env bash
# Pre-release validation helper for v1.0.0
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VERSION="$(tr -d ' \n\r' < VERSION)"
echo "==> Release candidate: $VERSION"

echo "==> Lint"
make lint

if command -v docker >/dev/null 2>&1 && docker compose ps --status running 2>/dev/null | grep -q api; then
  echo "==> Integration tests (Docker)"
  docker compose exec -T api pytest tests/integration -q
else
  echo "==> Skipping Docker tests (stack not running). Start with: make run"
fi

echo "==> Build production images"
docker build -f docker/Dockerfile -t "expensetracker-api:${VERSION}" .
docker build -f docker/Dockerfile.celery.prod -t "expensetracker-celery:${VERSION}" .

echo "==> Release candidate checks complete for $VERSION"
echo "Next: follow docs/deployment/staging-deployment.md"
