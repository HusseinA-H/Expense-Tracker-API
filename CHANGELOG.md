# Changelog

All notable changes to Expense Tracker API are documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.0.0] - 2026-06-20

### Added

- OAuth2 `/auth/token` endpoint for Swagger Authorize integration
- Enterprise README with architecture diagrams and badges
- Interactive HTML portfolio presentation (`docs/presentation/`)
- English PDF documentation (50+ pages)
- SVG visual assets (`docs/assets/`)
- MIT License, CONTRIBUTING.md
- Documentation restructure under `docs/` subdirectories

### Fixed

- `Dockerfile.celery.prod` now runs Celery worker (was incorrectly running uvicorn)
- OpenAPI security scheme aligned with OAuth2 password grant token URL

### Changed

- Version promoted from `1.0.0-rc.1` to `1.0.0`
- Enterprise `.gitignore` (excludes Arabic PDF, secrets, artifacts)

## [1.0.0-rc.1] - 2026-06-20

### Release candidate

- CI/CD pipelines (GitHub Actions: lint, test, image build/publish)
- Production Docker Compose overlay (`docker-compose.prod.yml`)
- Production Celery image (`docker/Dockerfile.celery.prod`)
- Nginx production config with security headers and rate limiting
- Readiness/liveness health endpoints (`/api/v1/health/live`, `/api/v1/health/ready`)
- Security hardening: CORS restrictions, TrustedHost, OpenAPI toggle, SECRET_KEY validation
- Documentation: README, architecture diagrams, deployment checklists, security review
- Version aligned to **1.0.0-rc.1** (API `APP_VERSION`)

### Added (since initial v1 feature set)

- Celery background jobs (email, budgets, reports, receipts, maintenance)
- Report export HTTP endpoints wired to Celery tasks
- Password reset request/confirm flow
- Receipt upload → `process_receipt_image` dispatch
- OpenTelemetry instrumentation (FastAPI, SQLAlchemy, Redis, Celery → Jaeger)

### Fixed

- Receipt upload file handling compatible with Starlette `UploadFile` API
- Admin authorization uses `AuthorizationError` (403) instead of misclassified 401


[1.0.0]: https://github.com/HusseinA-H/Expense-Tracker-API/releases/tag/v1.0.0
[1.0.0-rc.1]: https://github.com/HusseinA-H/Expense-Tracker-API/compare/v0.9.0...v1.0.0-rc.1
