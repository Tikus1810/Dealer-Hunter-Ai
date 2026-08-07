# Deployment & Operations (Band 13: Deployment_DevOps)

Band 13's spec (`Band 13/Band_13_Deployment_DevOps.md`) is a section-header
skeleton, not a filled specification (true of Bands 11–15 and 17–20 — see
the root [README.md](../README.md#status)) — everything below follows
standard industry practice for a small FastAPI + Postgres + Redis service,
not a documented Deal Hunter AI–specific requirement.

**Honesty note before anything else:** nothing in this document has been
exercised end-to-end. This was written without a Docker daemon, a
provisioned cloud/server account, or a GitHub remote available in the
sandbox that built it. Every piece (Dockerfile, compose files, CI/CD
workflow, migrations-on-startup) is individually reasoned-through and, where
possible, verified in isolation (e.g. the app code paths it depends on —
`/api/v1/ready`, `/metrics` — have real test coverage), but the deployment
mechanics themselves are a template to validate, not a proven pipeline.
Treat every instruction here as "run this and see" the first time, not
"this is known to work."

## Architecture

Single deployable backend service (`backend/`, one Docker image) plus two
managed dependencies it needs: PostgreSQL 16 and Redis 7. No message queue,
no separate worker process — the one piece of background work (marketplace
ingestion) runs as an in-process asyncio loop inside the same process that
serves HTTP (see "Scheduler" below). `mobile/` is a separate deployable
(app store builds), out of scope for this document.

```
                    ┌─────────────┐
   HTTP/HTTPS  ───▶  │   backend    │ ───▶ PostgreSQL 16
  (uvicorn:8000)     │  (1 process, │
                      │ ingestion    │ ───▶ Redis 7
                      │ loop inside) │
                      └─────────────┘
```

## Environments

Three environments are assumed, distinguished purely by `APP_ENV`/config,
not by different code paths:

| Environment | `APP_ENV`     | Purpose                                   |
| ----------- | ------------- | ------------------------------------------ |
| development | `development` | Local machine, `docker-compose.yml`, debug logging, `--reload` |
| staging     | `staging`     | Pre-production, same image as prod, real (but non-production) data |
| production  | `production`  | `docker-compose.prod.yml`, `APP_DEBUG=false` |

`Settings.is_production` (`backend/app/core/config.py`) is the one place
that branches on this — currently unused by anything except being available
for future use (e.g. gating docs exposure); nothing in this codebase
currently disables `/api/docs` in production. That's a Task #15
(Security-Härtung) candidate, not done here.

## Docker

`backend/Dockerfile` is a two-stage build:

1. **`builder`**: installs `build-essential`/`libpq-dev` and pip-installs
   `requirements.txt` into a venv (`/opt/venv`). Needed because some
   dependencies (e.g. `argon2-cffi`) compile a C extension.
2. **`runtime`**: `python:3.13-slim` + `curl` (for `HEALTHCHECK`) only —
   copies the built venv from `builder`, copies the app source, runs as a
   non-root `appuser`. Neither `asyncpg` nor `psycopg2-binary` need a
   system `libpq` at runtime (both bundle their own), so it isn't
   installed here — most of the image-size win over a single-stage build.

`docker-entrypoint.sh` (the image's `ENTRYPOINT`) runs `alembic upgrade
head` before `exec`-ing the `CMD` (`uvicorn ...`). This is correct for a
**single backend instance**. If this is ever scaled to multiple replicas,
move the migration step to a separate one-off release job instead —
concurrent `alembic upgrade head` invocations from every container's
startup could race each other. The script's own comment says the same
thing; keep both in sync if this changes.

`backend/.dockerignore` keeps `.env`, `.git`, caches, and `tests/` out of
the build context and the final image.

### Build & run locally

```bash
docker compose -f infra/docker/docker-compose.yml up --build
```

Brings up Postgres, Redis, and the backend (migrations run automatically on
container start). `backend/.env` (copied from `.env.example`) supplies
everything except `DATABASE_URL`/`DATABASE_URL_SYNC`/`REDIS_URL`, which the
compose file overrides to point at the `postgres`/`redis` services instead
of `.env`'s `localhost` defaults.

## CI/CD

- **CI** (`.github/workflows/ci.yml`, unchanged since Band 12/Task #13):
  lint (`ruff check`), format check (`ruff format --check`), type check
  (`mypy`), then the full test suite with coverage (`pytest --cov
  --cov-fail-under=80`) against real Postgres/Redis service containers.
  Also runs `flutter pub get`/`analyze`/`test --coverage` in a separate job.
- **CD** (`.github/workflows/cd.yml`, new in Task #14): triggered by
  `workflow_run` on the CI workflow completing successfully on `main` —
  deliberately *not* a parallel `push` trigger, so an image can never be
  built from a commit that hasn't passed CI. Builds `backend/` and pushes
  to `ghcr.io/<owner>/dealhunter-backend`, tagged with both the commit sha
  (`sha-<12 chars>` — what a rollback should pin to; immutable) and
  `latest` (a convenience pointer only).
- **Dependabot** (`.github/dependabot.yml`): weekly PRs for
  `backend/requirements.txt` (pip) and GitHub Actions action versions.
  Deliberately no `mobile/pubspec.yaml` (pub) entry yet — see the file's
  comment on why.

Neither workflow has ever actually run (no GitHub remote exists for this
repo in the sandbox that wrote them) — push to a real GitHub repo with a
`main` branch to find out if they're right.

## Secrets management

Nothing sensitive is ever committed. `.env` is gitignored;
`backend/.env.example` documents every variable with no real values.

- **Local/dev**: `.env` file, loaded by `pydantic-settings`
  (`backend/app/core/config.py`).
- **CI**: GitHub Actions' own ephemeral service containers + inline `env:`
  in `ci.yml` (a throwaway `ci-test-secret` JWT key — fine, this data never
  outlives the job).
- **CD (image push)**: `secrets.GITHUB_TOKEN` (built-in, scoped to
  `packages: write` for this one job) — no manually-managed secret needed
  for GHCR.
- **Production**: `docker-compose.prod.yml` takes every secret from the
  *deploying shell's* environment (`${VAR:?required}` syntax — fails
  loudly, not silently, if something's missing) — never from a file in the
  image or the repo. Where you actually source those values (a secrets
  manager, your CI/CD platform's secret store, a locked-down
  `EnvironmentFile` for systemd) depends on wherever this ends up deployed,
  which hasn't been decided yet (see "Known gaps" in the root README).

## Monitoring & logging

- **`GET /api/v1/health`** — liveness. No dependency checks, always `200`
  if the process can respond at all. This is what `Dockerfile`'s
  `HEALTHCHECK` uses — a DB/Redis blip should never make Docker (or an
  orchestrator relying on this) kill and restart an otherwise-fine process.
- **`GET /api/v1/ready`** — readiness. Runs `SELECT 1` against Postgres and
  `PING` against Redis; `200` with `{"status": "ok", "checks": {...}}` if
  both succeed, `503` with the specific failure(s) otherwise. Point an
  orchestrator's readiness probe (not liveness probe) at this one — during
  a Postgres failover it should stop routing traffic here, not restart the
  container.
- **`GET /metrics`** — Prometheus text exposition format
  (`app/core/metrics.py` + the middleware in `app/main.py`):
  `http_requests_total{method,path_template,status_code}` (counter) and
  `http_request_duration_seconds{method,path_template}` (histogram).
  `path_template` (e.g. `/api/v1/offers/{id}`), not the literal requested
  URL, keeps label cardinality bounded. No Prometheus server scrapes this
  anywhere yet — no monitoring stack is provisioned for this project (see
  "Known gaps"). The endpoint itself needs no external service to exist or
  be tested, which is why it has unit test coverage
  (`tests/unit/test_metrics.py`) despite that.
- **Logging**: structured JSON via `structlog`
  (`app/core/logging.py`, unchanged since Band 03), correlation IDs
  threaded through every request (`X-Correlation-ID` header,
  `app/main.py`'s `correlation_id_middleware`) and included in every log
  line via `structlog.contextvars`. Ships to stdout; a log aggregator
  (whatever the eventual hosting platform provides — CloudWatch, Loki, a
  managed platform's built-in log viewer) is expected to collect it from
  there, not something this repo configures.

## Scheduler (marketplace ingestion)

`AsyncIntervalScheduler` (`app/modules/offers/infrastructure/scheduler.py`,
built in Task #5) runs inside the same process as the API server —
`app/bootstrap.py::build_scheduler()` constructs it from `Settings`,
`app/main.py`'s `lifespan` calls `.start()`/`.stop()` around the app's own
lifetime. It is:

- **Off by default** (`SCHEDULER_ENABLED=false`) — no environment runs
  background network calls against eBay/Kleinanzeigen unless explicitly
  opted in.
- **A no-op even when enabled** unless a provider is actually configured
  (`EBAY_CLIENT_ID`+`EBAY_CLIENT_SECRET`, or
  `KLEINANZEIGEN_PROVIDER_ENABLED=true`) — logs a warning and runs zero
  jobs otherwise, rather than silently doing nothing without saying why.
- **Single-instance only.** This is an in-process asyncio loop, not a
  distributed job queue with locking — running it in more than one replica
  per environment would fetch/ingest the same listings redundantly from
  every replica. Harmless correctness-wise (`OfferRepositoryProtocol.
  upsert` is idempotent on `(source, source_listing_id)`), but wastes
  external API quota and rate-limit budget multiple times over. If this
  ever needs to run on more than one replica, extract it into its own
  single-replica deployment (a second image/service using the same
  codebase, just running a small script that calls `build_scheduler` +
  `.start()` instead of `uvicorn`) rather than enabling it broadly.

## Release process

1. Merge to `main` (via PR, after CI is green).
2. `cd.yml` fires automatically once CI's `main` run succeeds, builds and
   pushes `ghcr.io/<owner>/dealhunter-backend:sha-<12 chars>` +
   `:latest`.
3. On the deployment host, pull and restart:
   ```bash
   export IMAGE_TAG=sha-<12 chars>   # from the CD run, not :latest, for reproducibility
   docker compose -f infra/docker/docker-compose.prod.yml pull backend
   docker compose -f infra/docker/docker-compose.prod.yml up -d
   ```
   `docker-entrypoint.sh` runs the new image's pending migrations before
   the new `backend` container starts serving traffic.
4. Verify: `GET /api/v1/ready` returns `200`, `GET /api/v1/health` returns
   `200`, spot-check `GET /metrics` is being scraped if a monitoring stack
   exists yet.

## Rollback

Because every image is tagged with an immutable commit sha (not just
`latest`), rolling back is repointing `IMAGE_TAG` at the previous known-good
sha and re-running step 3 above:

```bash
export IMAGE_TAG=sha-<previous-good-12-chars>
docker compose -f infra/docker/docker-compose.prod.yml up -d
```

**Caveat:** this only rolls back application code. If the bad release
included a backward-incompatible migration (one that drops/renames a column
a previous version's code still reads), rolling back the image alone isn't
enough — you'd also need a corresponding "down" migration or a restore from
backup (see below). This repo's migrations (`backend/alembic/versions/`)
are hand-written and offline-verified in both directions
(`alembic upgrade head` / `alembic downgrade base`), but no *release*
process here has ever exercised an actual rollback against a real database
with real data — treat the first one as a drill, not routine.

## Backups & disaster recovery

No managed database/backup service is provisioned yet (see "Known gaps").
When one is chosen, prefer its built-in automated backups over a hand-rolled
cron job. Until then, the standard `pg_dump`/`pg_restore` pattern for the
`docker-compose.yml`/`docker-compose.prod.yml` `postgres` service:

```bash
# Backup (from the host, against the running postgres container)
docker compose -f infra/docker/docker-compose.prod.yml exec postgres \
  pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB" > "dealhunter-$(date +%F).dump"

# Restore into a fresh/empty database
docker compose -f infra/docker/docker-compose.prod.yml exec -T postgres \
  pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists < dealhunter-2026-08-07.dump
```

Retention/schedule (e.g. "daily dumps, keep 30 days") is a decision for
whoever operates the real deployment — not made here since there's no real
data volume or compliance requirement to size it against yet. Redis holds
no data this product can't reconstruct (caching only, per Band 09), so it's
deliberately excluded from the backup story.

**Disaster recovery** (total loss of the deployment host): the Postgres
volume is the only state that can't be rebuilt from code — restore the most
recent `pg_dump`, redeploy the latest (or last known-good) image per
"Release process" above, and reapply any Redis-only state (nothing
persistent lives there) is a no-op by design.

## Known gaps

- No cloud/server account is provisioned for this project — every piece
  above is a template to run somewhere, not a description of a live
  system. Choosing a host (a VPS, a managed container platform, a specific
  cloud) is an open decision.
- No monitoring/alerting stack (Prometheus + Grafana, or a managed
  equivalent) is deployed to actually scrape `/metrics` — the endpoint
  works, nothing reads it yet.
- No managed Postgres backup service is chosen — see "Backups" above.
- `docker-entrypoint.sh`'s migrate-on-startup approach doesn't scale past
  one backend replica without modification — see "Scheduler" and the
  script's own comment for the same caveat applied to two different
  pieces.
- Rate limiting, secrets rotation, and dependency vulnerability scanning
  are explicitly **not** covered here — that's Band 14/Task #15
  (Security-Härtung) territory.
