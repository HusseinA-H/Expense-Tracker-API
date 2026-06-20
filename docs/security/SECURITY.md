# Security Hardening Review

Release candidate **1.0.0-rc.1** — deployment and reliability focus.  
No new business features; documents posture and residual risks.

---

## Summary

| Area | Status | Notes |
|------|--------|-------|
| Authentication | ✅ Solid | JWT + refresh rotation, Redis token blacklist on logout |
| Authorization | ✅ Fixed | Admin routes use proper 403 via `AuthorizationError` |
| Password storage | ✅ Solid | bcrypt hashing, strength validation on register/reset |
| Transport | ⚠️ Ops | TLS termination expected at Nginx/load balancer (not in repo) |
| CORS | ✅ Hardened | Explicit origins required in staging/production |
| OpenAPI | ✅ Hardened | Disabled via `OPENAPI_ENABLED=false` in prod env template |
| Secrets | ✅ Hardened | `SECRET_KEY` length/placeholder validation in prod/staging |
| Headers | ✅ Hardened | Nginx prod adds X-Content-Type-Options, X-Frame-Options, etc. |
| Rate limiting | ⚠️ Basic | Nginx `limit_req` only; no app-level per-user limits |
| Audit | ✅ Solid | Append-only logs, partitioned table |
| Dependencies | ⚠️ Monitor | Pin in `requirements.txt`; enable Dependabot in GitHub |
| Container | ✅ Solid | Non-root user, multi-stage builds, health checks |
| Observability | ✅ Solid | OpenTelemetry → Jaeger; no PII in span attributes by default |

**Overall:** Acceptable for **staging** and **controlled production** rollout after checklist sign-off.

---

## Implemented hardening (this release)

### Application

- **`CORS_ORIGINS`**: comma-separated list; rejects `*` in staging/production at startup
- **`OPENAPI_ENABLED`**: set `false` in `.env.production.example`
- **`TRUSTED_HOSTS`**: `TrustedHostMiddleware` enabled in staging/production
- **`SECRET_KEY` validator**: rejects short/placeholder values in staging/production
- **CORS methods/headers**: restricted to required set (no wildcard methods)
- **Health endpoints**: `/health/live` vs `/health/ready` for safe orchestration

### Infrastructure

- **Nginx** (`docker/nginx/nginx.prod.conf`): security headers, rate limit, hidden server tokens
- **Docker**: non-root runtime, resource limits in prod compose, JSON log rotation
- **Postgres/Redis**: not published on host ports in prod overlay
- **Flower/Jaeger/Grafana**: behind `observability` profile — do not expose publicly in production without auth/VPN

### Process

- **CI**: lint + integration tests on every PR
- **CD**: reproducible image builds, versioned artifacts
- **Checklists**: staging and production gates documented

---

## Residual risks & recommendations

### High priority (before public production)

1. **TLS 1.2+** — terminate HTTPS at Nginx or cloud LB; redirect HTTP→HTTPS
2. **Secret management** — use vault/K8s secrets instead of flat `.env` on disk
3. **SMTP credentials** — rotate; restrict egress from worker containers
4. **Database** — enable automated backups, test restore, encryption at rest if cloud-managed
5. **CORS** — set exact frontend origin(s) per environment

### Medium priority

1. **Rate limiting** — add Redis-backed limits on auth endpoints (`/login`, password reset)
2. **Refresh token binding** — optional device fingerprint / rotation anomaly detection
3. **Audit log retention** — operational `archive_old_partitions` beyond metadata stub before high volume
4. **Dependency scanning** — `pip-audit`, GitHub Dependabot, base image updates
5. **WAF** — cloud WAF in front of Nginx for OWASP Top 10 coverage

### Low priority / post-v1.0.0

1. API v2 (explicitly out of scope)
2. mTLS between internal services (if multi-host K8s)
3. Field-level encryption for sensitive metadata

---

## Security checklist (quick audit)

- [ ] `SECRET_KEY`, `DB_PASSWORD`, `REDIS_PASSWORD` unique per environment
- [ ] `.env.production` not committed (verified in `.gitignore`)
- [ ] `OPENAPI_ENABLED=false` in production
- [ ] `CORS_ORIGINS` set to real frontend URL(s)
- [ ] Nginx/LB TLS configured with valid certificates
- [ ] Postgres/Redis not reachable from public internet
- [ ] Flower/Grafana/Jaeger not public without authentication
- [ ] SMTP provider SPF/DKIM configured for sending domain
- [ ] Backup and restore drill completed
- [ ] Incident response contact documented

---

## Reporting

Report security issues through your organization's private channel before public release.
