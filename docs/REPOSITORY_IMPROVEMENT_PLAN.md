# Repository Improvement Plan

**Audit date:** 2026-06-20  
**Target release:** v1.0.0 (public GitHub flagship portfolio)

---

## Executive summary

The Expense Tracker API is a production-grade FastAPI application with layered architecture, Celery background jobs, OpenTelemetry observability, Docker-based deployment, and GitHub Actions CI/CD. The codebase is **release-ready** with minor hygiene and documentation gaps addressed in this release preparation.

---

## Phase 1 — Audit findings

### Strengths

| Area | Status |
|------|--------|
| Layered architecture (API → Service → UoW → Repository) | ✅ Solid |
| JWT + refresh rotation + Redis blacklist | ✅ Implemented |
| Integration tests (47 tests incl. OAuth2) | ✅ Passing in Docker |
| Docker dev + prod overlay | ✅ Complete |
| CI lint + test + image build | ✅ Configured |
| Observability (Jaeger, Prometheus, Grafana) | ✅ Wired |
| Security hardening (CORS, TrustedHost, OpenAPI toggle) | ✅ Documented |

### Issues identified & resolution

| Issue | Severity | Action |
|-------|----------|--------|
| `Dockerfile.celery.prod` ran uvicorn instead of Celery | **Critical** | Fixed — Celery worker CMD |
| OAuth2/Swagger tokenUrl mismatch | **High** | Fixed — `/auth/token` endpoint |
| Docs scattered at repo root | Medium | Restructured under `docs/` |
| `.gitignore` incomplete | Medium | Enterprise `.gitignore` |
| No public README / portfolio assets | Medium | World-class README + presentation |
| `implementation_plan.md` at root | Low | Moved to `docs/archive/` |
| `.pytest_cache` on disk | Low | Ignored, not tracked |
| `.env` with dev secrets on disk | Low | Ignored, never commit |
| `API_V2_STR` unused | Low | Retained (future); documented |
| CD smoke job placeholder | Low | Documented in deployment guide |
| Proprietary license | Medium | MIT for open-source release |

### Dead / duplicate / artifact files

- **`.pytest_cache/`** — test artifact (gitignored)
- **`implementation_plan.md`** — dev planning doc → archived
- **Legacy `/expenses` API** — intentional backward compatibility (not dead)
- **`Dockerfile.celery.prod`** — was duplicate of API image (fixed)

### Secrets audit

| File | Risk | Mitigation |
|------|------|-----------|
| `.env` | Local dev secrets | In `.gitignore` |
| `.env.example` | Example defaults only | Safe to commit |
| `.env.production.example` | Placeholders only | Safe to commit |
| CI workflow secrets | Test-only values | Acceptable for CI |

---

## Phase 2 — Restructure (completed)

```
docs/
├── README.md                 # Documentation index
├── REPOSITORY_IMPROVEMENT_PLAN.md
├── architecture/
│   └── architecture.md
├── deployment/
│   ├── staging-deployment.md
│   └── production-readiness.md
├── security/
│   └── SECURITY.md
├── release/
│   └── RELEASE_v1.0.0.md
├── archive/
│   └── implementation_plan.md
├── assets/                   # SVG diagrams
├── presentation/             # Interactive HTML portfolio
├── pdf/                      # PDF generation sources
└── Expense_Tracker_API_Documentation_EN.pdf
```

Application code (`app/`) unchanged — already enterprise-grade FastAPI layout.

---

## Phase 3–9 — Deliverables checklist

- [x] Enterprise `.gitignore`
- [x] Fix production Celery Dockerfile
- [x] Docs restructure + link updates
- [x] World-class README
- [x] English PDF documentation (50+ pages)
- [x] Arabic PDF (local only, gitignored)
- [x] Interactive HTML presentation
- [x] Visual SVG assets
- [x] VERSION → 1.0.0
- [x] Integration test validation
- [x] Logical git commits + tag v1.0.0

---

## Future roadmap (post v1.0.0)

1. Unit test layer (`tests/unit/`)
2. Real CD smoke tests against staging URL
3. API v2 when requirements stabilize
4. Rate limiting middleware (beyond Nginx)
5. Kubernetes Helm chart
6. OpenAPI client SDK generation
