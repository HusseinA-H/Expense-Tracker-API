# Release v1.0.0 Preparation

Step-by-step guide to promote release candidate **1.0.0-rc.1** to **v1.0.0 GA**.

---

## Versioning

| Artifact | RC value | GA value |
|----------|----------|----------|
| [VERSION](../VERSION) | `1.0.0-rc.1` | `1.0.0` |
| `APP_VERSION` env | `1.0.0-rc.1` | `1.0.0` |
| Git tag | `v1.0.0-rc.1` (optional) | `v1.0.0` |
| Docker image tag | `1.0.0-rc.1` | `1.0.0` |

---

## Phase 1 — Release candidate validation

1. Run local/CI validation:

   ```bash
   bash scripts/release-prepare.sh
   ```

2. Deploy to staging:

   ```bash
   cp .env.production.example .env.staging
   # edit secrets
   bash scripts/deploy-staging.sh .env.staging
   ```

3. Complete [staging-deployment.md](../deployment/staging-deployment.md)

---

## Phase 2 — Promote to v1.0.0

1. Update version files:

   ```bash
   echo "1.0.0" > VERSION
   # set APP_VERSION=1.0.0 in .env.production.example (documentation)
   # update pyproject.toml [project].version
   # update CHANGELOG.md [1.0.0] section with date
   ```

2. Update [CHANGELOG.md](../CHANGELOG.md) — move items from RC to GA section

3. Commit on `main` (or `release/1.0.0` branch):

   ```bash
   git add VERSION CHANGELOG.md pyproject.toml app/config.py
   git commit -m "Prepare release v1.0.0"
   ```

4. Create annotated tag:

   ```bash
   git tag -a v1.0.0 -m "Expense Tracker API v1.0.0"
   git push origin main
   git push origin v1.0.0
   ```

5. CD workflow builds and publishes:

   - `ghcr.io/<org>/api:1.0.0`
   - `ghcr.io/<org>/celery:1.0.0`
   - Deployment bundle artifact

---

## Phase 3 — Production deploy

1. Prepare `.env.production` (see [.env.production.example](../.env.production.example))
2. Complete [production-readiness.md](../deployment/production-readiness.md)
3. Deploy:

   ```bash
   export APP_VERSION=1.0.0
   docker compose -f docker-compose.yml -f docker-compose.prod.yml \
     --env-file .env.production up -d
   docker compose -f docker-compose.yml -f docker-compose.prod.yml \
     --env-file .env.production exec api alembic upgrade head
   ```

4. Run production smoke tests (see readiness checklist)
5. Enable monitoring hypercare for 72 hours

---

## Phase 4 — GitHub Release

1. Create GitHub Release from tag `v1.0.0`
2. Attach `release-1.0.0.tar.gz` from CD artifacts
3. Paste CHANGELOG excerpt
4. Link to README and architecture docs

---

## Rollback plan

| Step | Action |
|------|--------|
| 1 | Route traffic away / enable maintenance page |
| 2 | `docker compose ... pull` previous image tag |
| 3 | `docker compose up -d` with `APP_VERSION=<previous>` |
| 4 | Verify `/health/ready` |
| 5 | Post-mortem if data migration occurred |

Database rollback: restore from pre-cutover backup (migrations are forward-only — test downgrade strategy in staging).

---

## Out of scope for v1.0.0

- API v2 endpoints
- New business features
- Distributed event bus

Track these in a post-GA roadmap.

---

## Quick

- [README.md](../README.md)
- [architecture.md](architecture.md)
- [SECURITY.md](SECURITY.md)
