# Production Readiness Checklist

Gate for promoting **v1.0.0** after successful staging sign-off.

---

## 1. Code & release artifact

- [ ] Staging checklist completed and signed off
- [ ] `CHANGELOG.md` updated for `1.0.0`
- [ ] [VERSION](../VERSION) set to `1.0.0`
- [ ] Git tag `v1.0.0` created and pushed
- [ ] CD workflow published images: `ghcr.io/<org>/api:1.0.0` and `celery:1.0.0`
- [ ] Deployment bundle artifact downloaded from GitHub Actions

---

## 2. Configuration

- [ ] `.env.production` created (never committed)
- [ ] All secrets rotated from staging (independent values)
- [ ] `ENVIRONMENT=production`
- [ ] `OPENAPI_ENABLED=false`
- [ ] `CORS_ORIGINS` = production frontend origin(s) only
- [ ] `TRUSTED_HOSTS` = production domain(s)
- [ ] SMTP production provider verified (SPF, DKIM, DMARC)
- [ ] `OTEL_EXPORTER_ENDPOINT` points to production collector
- [ ] Resource limits reviewed for expected load

---

## 3. Infrastructure

- [ ] TLS certificates installed and auto-renewal configured
- [ ] HTTP → HTTPS redirect enabled
- [ ] Postgres: backups automated (RPO ≤ 24h), restore tested
- [ ] Redis: persistence/AOF configured if required
- [ ] Shared volumes for `uploads/`, `exports/` backed up or on durable storage
- [ ] Postgres and Redis **not** exposed on public ports
- [ ] Observability stack (Flower, Grafana, Jaeger) on private network or SSO
- [ ] Log aggregation configured (JSON file → central store)
- [ ] Container restart policy `unless-stopped` verified

---

## 4. Database

- [ ] `alembic upgrade head` run against production (once, during cutover window)
- [ ] Connection pool sizes appropriate for instance count
- [ ] Read replica configured (if used) and monitored
- [ ] Audit partition strategy documented for ops team

---

## 5. Security

- [ ] [SECURITY.md](../SECURITY.md) residual high-priority items addressed or accepted with sign-off
- [ ] Dependabot / `pip-audit` clean or exceptions documented
- [ ] Admin accounts limited; break-glass procedure documented
- [ ] Rate limits validated under load test
- [ ] Password reset flow tested end-to-end with production SMTP

---

## 6. Reliability & performance

- [ ] Readiness probe wired to load balancer / orchestrator
- [ ] Liveness probe configured with appropriate timeouts
- [ ] Load test baseline (e.g. Locust from dev deps) — document RPS/latency
- [ ] Celery worker count sized for email + report workload
- [ ] Beat schedule confirmed (hourly budgets, daily token cleanup)

---

## 7. Monitoring & alerting

- [ ] Alerts: API 5xx rate, readiness failures, DB connectivity, Redis, Celery queue depth
- [ ] Grafana dashboards imported (or minimal panels created)
- [ ] On-call rotation and runbook linked
- [ ] Jaeger sampling rate acceptable for production traffic

---

## 8. Cutover & rollback

- [ ] Maintenance window communicated
- [ ] Rollback image tag identified: _______________
- [ ] Rollback procedure tested in staging
- [ ] Post-deploy smoke script executed within 15 minutes of cutover
- [ ] 24h hypercare period scheduled

---

## 9. Smoke test (production)

Run against production URL (replace host):

```bash
BASE=https://api.example.com/api/v1
curl -sf "$BASE/health/ready"
# Manual or scripted auth + transaction + report queue checks
```

- [ ] Health ready OK
- [ ] Auth login OK
- [ ] Create/read transaction OK
- [ ] Report export queues and completes
- [ ] No OpenAPI exposure at `/docs`

---

## Sign-off

| Area | Approver | Date | Approved |
|------|----------|------|----------|
| Engineering Lead | | | ☐ |
| DevOps / SRE | | | ☐ |
| Security | | | ☐ |
| Product Owner | | | ☐ |

**Production go-live authorized:** ☐ Approved ☐ Blocked

Notes: _____________________________________________________________

---

## Post-release (72h)

- [ ] Monitor error rates, latency, Celery failures
- [ ] Verify backup job ran successfully
- [ ] Confirm email deliverability metrics
- [ ] Close release ticket; archive deployment log
