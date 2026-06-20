# Staging Deployment Checklist

Use this checklist when deploying **1.0.0-rc.1** (or later RC) to staging.

---

## Pre-deploy

- [ ] Create `.env.staging` from [`.env.production.example`](../.env.production.example)
- [ ] Generate `SECRET_KEY` (≥32 chars): `python -c "import secrets; print(secrets.token_urlsafe(48))"`
- [ ] Set unique `DB_PASSWORD`, `REDIS_PASSWORD`, `GRAFANA_PASSWORD`
- [ ] Set `CORS_ORIGINS` to staging frontend URL(s)
- [ ] Set `TRUSTED_HOSTS` to staging hostname(s)
- [ ] Set `OPENAPI_ENABLED=false` (recommended)
- [ ] Configure real SMTP credentials (or staging mail sink)
- [ ] Confirm `APP_VERSION` matches [VERSION](../VERSION)
- [ ] CI green on target commit ([GitHub Actions](../.github workflows/ci.yml))

---

## Deploy

```bash
bash scripts/deploy-staging.sh .env.staging
```

Or manual steps:

- [ ] `docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.staging build`
- [ ] Start Postgres + Redis; wait for healthy
- [ ] `alembic upgrade head` via api container
- [ ] Start api, celery-worker, celery-beat, nginx
- [ ] Optional: `--profile observability` for Jaeger/Grafana/Flower

---

## Post-deploy verification

### Health

- [ ] `curl -sf http://<staging-host>/api/v1/health/live`
- [ ] `curl -sf http://<staging-host>/api/v1/health/ready` returns `"status":"ok"`

### Smoke tests

- [ ] `POST /api/v1/auth/register` — 201
- [ ] `POST /api/v1/auth/login` — 200 + tokens
- [ ] `GET /api/v1/users/me` — 200 with JWT
- [ ] `POST /api/v1/transactions` — 201
- [ ] `POST /api/v1/budgets` — 201
- [ ] `POST /api/v1/reports/export/csv` — 202 + `task_id`
- [ ] Poll `GET /api/v1/reports/tasks/{task_id}` until completed
- [ ] `POST /api/v1/auth/password-reset/request` — 204

### Background workers

- [ ] Celery worker logs show task registration
- [ ] Flower (if enabled) lists workers at `:5555`
- [ ] Welcome email task fires on registration (check SMTP sink)
- [ ] CSV file appears under shared `exports/` volume

### Observability

- [ ] Traces visible in Jaeger for API request (if profile enabled)
- [ ] Nginx access logs flowing
- [ ] No stack traces in API logs at INFO level for normal requests

---

## Regression

- [ ] Run integration suite against staging DB snapshot (optional):  
      `pytest tests/integration -v` from CI-equivalent runner
- [ ] Verify OpenAPI disabled when `OPENAPI_ENABLED=false` (`/docs` → 404)

---

## Sign-off

| Role | Name | Date | OK |
|------|------|------|-----|
| Engineering | | | ☐ |
| QA | | | ☐ |
| Security | | | ☐ |

**Approved for production readiness review:** ☐ Yes ☐ No — notes: _______________

---

## Rollback

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.staging down
# redeploy previous image tag from GHCR
export APP_VERSION=<previous-tag>
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.staging up -d
```
