# Deal Hunter AI

Production-grade AI platform that discovers, evaluates and prioritizes
second-hand technology deals (Windows laptops, MacBooks, iPhones, game
consoles) — explainable Deal Score, repair economics, and push
notifications for saved searches.

Specification source: `Band 1/` … `Band 20/` (see [Band 1](Band%201/Band_01_Master_PRD.md)
for the master PRD). Each `Band N/` folder is the original spec input and is
kept as-is for traceability; this repo implements it incrementally.

Contributing to this repo (human or Claude Code)? Read [`CLAUDE.md`](CLAUDE.md)
first — architecture/module boundaries, naming conventions, quality gates,
testing conventions and commit conventions, all consolidated from Bands
1–17's actual implementation history (Band 17: Claude_Context).

## Repository layout

```
backend/    FastAPI backend, Clean Architecture (Python 3.13)
mobile/     Flutter app (Android/iOS)
infra/      Docker Compose, deployment config
.github/    CI workflows
Band 1..20/ Original specification documents (do not edit — reference only)
```

## Backend architecture

Modular monolith, one folder per bounded context under `backend/app/modules/`:
`auth`, `users`, `offers`, `search`, `scoring` (DealBrain), `repair`
(RepairBrain), `notifications`, `analytics`. Each module is layered:

```
modules/<name>/
  domain/          entities — no framework/DB dependency
  application/      use cases + the module's public interface (Protocol)
  infrastructure/    SQLAlchemy repos, external providers, adapters
  presentation/       FastAPI routers + Pydantic DTOs
```

Other modules and the API layer may only depend on `application/interfaces.py`
of a module — never reach into its `infrastructure/`.

## Local development

```bash
cd backend
cp .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Or via Docker Compose (Postgres + Redis + backend):

```bash
docker compose -f infra/docker/docker-compose.yml up --build
```

Liveness: `GET http://localhost:8000/api/v1/health` (process is up, no dependency checks)
Readiness: `GET http://localhost:8000/api/v1/ready` (DB + Redis reachable — 503 if not)
Metrics: `GET http://localhost:8000/metrics` (Prometheus text format)
API docs: `http://localhost:8000/api/docs`

## Tests (Band 12: Testing_QA)

```bash
cd backend
pytest -m "not integration"   # unit tests only, no services required (~86% coverage alone)
pytest                        # full suite — needs Postgres+Redis (see docker-compose above)
```

**Strategy:**

- **Unit tests** (`tests/unit/`) — one file per module/component, run
  against in-memory fakes for every port (repository/sender/client
  Protocols). No DB, no network, no `@pytest.mark.integration`. This is
  the tier that actually runs in a sandbox with no Postgres available —
  every module's business logic (analyzers, services, controllers) is
  fully exercised here.
- **Integration tests** (`tests/integration/`) — real HTTP requests
  (`httpx.AsyncClient` + `ASGITransport`) against the actual FastAPI app,
  or direct repository tests, both against a real (ephemeral,
  transaction-rolled-back) PostgreSQL database. Marked
  `@pytest.mark.integration`; only these need Postgres/Redis, which is why
  they're excluded from the fast local loop and run in CI instead
  (`.github/workflows/ci.yml`'s `backend` job spins up both as services).
- **Mocking external HTTP** (eBay API, eBay Kleinanzeigen, Claude Vision,
  Firebase) uses `respx` (for `httpx`-based clients — the `anthropic` SDK
  and eBay providers) or a small constructor-injected `send_fn`/`client`
  seam (for SDKs that don't expose their transport directly, e.g.
  `firebase_admin.messaging` — see `FcmNotificationSender`'s doc comment).
  Nothing here ever hits a real third-party API.
- **Coverage gate**: `--cov-fail-under=80` in CI, run against the full
  suite (unit + integration). The unit-only tier alone already reaches
  ~86% locally; the remaining infrastructure/presentation-layer code
  (SQLAlchemy repositories, FastAPI routers) is what the integration tier
  covers instead of duplicating with more fakes.
- **Static analysis as a test-equivalent gate**: `ruff check`, `ruff
  format --check`, and `mypy --strict` all run in CI and must pass — mypy
  strict mode has caught real bugs during development (see git history),
  not just style nits.
- **Local pre-commit hooks** (`.pre-commit-config.yaml`, run `pip install
  pre-commit && pre-commit install` once) catch `ruff`/formatting issues
  before they reach CI. Deliberately excludes mypy/pytest — both need the
  venv active and are slow enough that CI is the right place for them.
- **Flutter** (`mobile/`): `flutter test` (unit tests against fakes, same
  philosophy as the backend — no widget/golden tests yet, see
  `mobile/README.md`'s "Known gaps") + `flutter analyze` in the `flutter`
  CI job. No coverage gate yet — enforcing one before the code has ever
  been verified against a real Flutter SDK would be premature (see
  `mobile/README.md`'s "Status").

## Database

```bash
cd backend
alembic upgrade head        # apply migrations
python -m scripts.seed      # seed the 4 primary device categories
```

## Marketplace Engine

`backend/app/modules/offers/` implements the Band 07 pipeline (Source →
Provider → Fetch → Normalize → Validate → Deduplicate → Persist), with two
providers:

- **`EbayApiProvider`** — eBay.com/eBay.de's official Browse API (OAuth2
  client-credentials). Needs `EBAY_CLIENT_ID`/`EBAY_CLIENT_SECRET` in `.env`
  (a registered eBay developer application) — without them it raises a
  clear error rather than silently returning nothing.
- **`KleinanzeigenProvider`** — see the ToS note below. CSS selectors were
  confirmed against the live site on 2026-08-05; re-verify before relying
  on them, markup changes are expected over time.

Both implement the same `MarketplaceProviderProtocol`, so `IngestionService`
and `AsyncIntervalScheduler` (the scheduler foundation) work identically
regardless of source.

## DealBrain (scoring)

`backend/app/modules/scoring/` implements the Band 05 architecture:
`PriceAnalyzer`, `SpecificationAnalyzer`, `SellerAnalyzer`, `RiskAnalyzer`,
`RepairFeasibilityAnalyzer` (domain/analyzers.py, each pure and independently
testable) → `ScoringEngine` combines their `AnalyzerOutput`s into a
0-100 score → `ExplanationGenerator` derives the recommendation label and
orders factors by impact. `GET /api/v1/offers/{id}/deal-score` computes,
persists (append-only, versioned via `scoring_version`) and returns a score.

**The v1 scoring weights are a documented starting point, not a spec-mandated
formula** — Band 05 defines principles (explainable, deterministic, unknown
values reduce confidence not correctness, no hidden rules) but not concrete
numbers. Market value is estimated from the median price of comparable
active listings in the same category (DealBrain has no external pricing
data source); confidence drops sharply below 3 comparables. Expect to tune
the constants in `domain/analyzers.py` once real usage data exists.

## RepairBrain (repair analysis)

`backend/app/modules/repair/` implements the Band 06 architecture:
`FaultAnalyzer` (splits `reported_defects` — confirmed facts — from
listing-text keyword matches — inferred assumptions) → `TimeEstimator` +
`PartsResolver` (parts and tools, independent from scoring per Band 06) →
`CostEstimator` → `RepairScoringEngine` → `RecommendationGenerator` (every
inferred fault gets its own risk note, satisfying Band 06's "mark uncertain
estimates clearly"). `POST /api/v1/offers/{id}/repair-report` computes,
persists (append-only, versioned via `report_version`) and returns a report.
DealBrain's `RepairFeasibilityAnalyzer` (Task #6) can fold a `RepairReport`
into a deal score once a caller has both — that wiring happens in Task #9.

Same honesty note as DealBrain: part prices, labor rates and repair times
in `domain/catalog.py` are indicative reference values, not a live
parts-supplier feed — there is no such data source yet.

## Vision AI

`backend/app/modules/vision/` implements the Band 08 architecture, scoped
to what's achievable without a vision-model credential (see "Known gaps"):
`ImagePreprocessor` (fetches + decodes each listing image; a fetch/decode
failure becomes an "unreachable" observation, not an aborted analysis) →
`ObservationEngine` (classical blur detection via edge-variance, plus a
resolution check) → `ConfidenceEstimator` (penalizes both poor image
quality and an incomplete image set) → `OutputFormatter`.
`GET /api/v1/offers/{id}/vision-observation` — compute-only, not persisted
(no `vision_observations` table exists; add one if/when DealBrain or
RepairBrain need to consume stored observations instead of calling this
endpoint directly).

**Cosmetic-damage detection: `ClaudeCosmeticConditionAnalyzer`** (in
`infrastructure/claude_vision_provider.py`) calls the Claude API's vision
capability with structured outputs (`messages.parse`, a Pydantic schema) to
classify condition, list clearly-visible damage separately from uncertain
notes, and flag likely-missing accessories — all from the listing photos
only, with an explicit instruction to answer "unclear" rather than guess.
It's wired in automatically once `ANTHROPIC_API_KEY` is set in `.env`;
without it, `cosmetic_condition` stays `"not_available"` with a note
explaining why, exactly as before — the honesty behavior from Band 08's
"distinguish observed facts from uncertain inferences" now covers both "we
determined nothing" (no key configured) and "the model itself is unsure"
(low `confidence` on a real assessment). If the Claude call fails or
refuses, the service catches it and falls back to `"not_available"` rather
than failing the whole request — image-quality checks always still run.
Model defaults to `claude-opus-5` (Anthropic's own guidance: never
downgrade for cost without an explicit decision); override
`ANTHROPIC_VISION_MODEL` for cheaper/faster triage at lower accuracy if
you're running this at high volume.

## REST API (Band 10)

All resource groups from Band 10 are now mounted under `/api/v1`:

- **Offers** — `GET /api/v1/offers?category=&page=&page_size=` (paginated
  list, `page`/`page_size` are page-based per Band 10's "cursor OR
  page-based" allowance — cursor-based was tried first and reverted, see
  the note below) and `GET /api/v1/offers/{offer_id}` (detail). Read-only,
  unauthenticated, same as DealBrain/RepairBrain/Vision.
- **Favorites** — `POST` / `DELETE /api/v1/offers/{offer_id}/favorite` and
  `GET /api/v1/favorites?page=&page_size=`. Requires auth; adding a
  duplicate favorite is `409 Conflict`, favoriting an unknown offer is `404`.
- **Search Profiles** — full CRUD under `/api/v1/search-profiles`, all
  user-scoped (a profile is invisible to, and unmodifiable by, anyone but
  its owner — enforced by returning `404` rather than `403` for
  someone-else's-profile, to avoid leaking existence). `SearchService.
  match_offer_against_profiles` (`app/modules/search/application/service.py`)
  is the matching engine notifications call: category is an exact match,
  keywords is a case-insensitive substring check, price bounds are
  inclusive, and `min_deal_score` requires an already-persisted DealBrain
  score for that offer — same "v1 heuristic, not spec-mandated" honesty
  note as DealBrain/RepairBrain. Profiles with `notify_on_match=False` are
  excluded from matches entirely.
- **Notifications** — see the dedicated section below.

**Pagination note:** offer listing was originally attempted as cursor-based
(`id > cursor` ordered by `created_at`), but UUIDs aren't monotonic with
insertion order, so that cursor silently skipped/repeated rows. Switched to
page-based (`OFFSET`/`LIMIT` on a stable `created_at DESC, id DESC` order)
before this ever shipped — `OfferRepositoryProtocol.list_by_category` takes
`page`/`page_size`, and `count_by_category` provides the total for `total`/
`page`/`page_size` response metadata.

## Notifications (Band 11)

`backend/app/modules/notifications/` implements the Band 11 architecture:
templates (`domain/templates.py`, German-only for now — this product's
actual market), preferences (`domain/preferences.py`: opt-out model, a user
only needs a row for what they've turned *off*), `NotificationService`
(persists a `Notification` per enabled channel — the audit log — then
best-effort delivers via FCM/Resend), `FcmNotificationSender`
(`infrastructure/fcm_provider.py`, wraps `firebase_admin.messaging.send` in
`asyncio.to_thread` since the SDK has no native async support), and
`ResendEmailSender` (`infrastructure/resend_provider.py`, calls Resend's
REST API directly via `httpx` — no SDK dependency for one endpoint).

**Event routing:** `SavedSearchMatchNotifier`
(`application/match_notifier.py`) implements `OfferPersistedHookProtocol`
(`app/modules/offers/application/interfaces.py`) — the "Trigger Analysis"
extension point `IngestionService` always had. `AsyncIntervalScheduler`
(Band 07/13) takes a `hook_factory: Callable[[AsyncSession], ...]`, not a
fixed instance — a fresh `SavedSearchMatchNotifier` per job, bound to that
job's own DB session, since it needs to read back the just-persisted offer
before the transaction commits. `app/bootstrap.py` (Task #14) wires the
real one in; every newly persisted offer is matched against active saved
searches (`SearchService.match_offer_against_profiles`) and each match
becomes a notification, without the `offers` module ever importing
`notifications` or `search` directly — the hook is a `Protocol` the
composition root satisfies with a concrete implementation (Band 2
module-boundary rule).

REST surface: `POST`/`DELETE /api/v1/notifications/devices` (register/
unregister an FCM device token), `GET /api/v1/notifications` (paginated
inbox), `POST /api/v1/notifications/{id}/read`, `GET`/`PUT
/api/v1/notifications/preferences`. All user-scoped, all require auth.

**Both PUSH and EMAIL are delivered when configured** (found and closed
in a later review pass — EMAIL was previously recorded but never sent).
Without `FCM_PROJECT_ID`/`FCM_CREDENTIALS_JSON_PATH` or
`RESEND_API_KEY`/`RESEND_FROM_EMAIL` set, notifications still work
end-to-end (persisted, listed, marked read, preferences) — delivery on
that channel is just skipped, same pattern as every other optional
provider in this codebase (eBay, Claude Vision).

## Flutter App (Band 4 / Band 18)

`mobile/` implements Band 4 end-to-end: feature-first Clean Architecture,
Riverpod 2.x state management, go_router navigation (auth-gated), a
Material 3 light/dark design system built from token files (brand
color/typography/app-icon decisions: [docs/branding.md](docs/branding.md),
Band 19), and every Band 4 "Core Feature" with real UI wired against the
real backend API —
Authentication, Dashboard, Search Profiles (full CRUD), Offer List/
Details, Deal Analysis, Repair Analysis, Favorites, Notifications
(inbox + preferences), Settings. See [mobile/README.md](mobile/README.md)
for the full architecture writeup, including the **"not yet verified
against a real Flutter SDK"** caveat — this repo's sandbox has no Flutter
toolchain, so `flutter pub get`/`analyze`/`test` need to be run for the
first time by whoever picks this up next (82 files, ~4200 lines, all
individually checked against current package docs while writing them —
see mobile/README.md's "Status" for exactly what that does and doesn't
cover).

## Deployment & Monitoring (Band 13)

Full writeup — environments, release process, rollback, backups, disaster
recovery — in [docs/deployment.md](docs/deployment.md). Summary:

- **Docker**: multi-stage `backend/Dockerfile` (build tools never ship in
  the runtime image). `docker-entrypoint.sh` runs `alembic upgrade head`
  before starting `uvicorn` — correct for the single-instance setup this
  repo ships (`infra/docker/docker-compose.yml`); see the script's own
  comment before scaling to multiple replicas.
- **CI/CD**: `.github/workflows/ci.yml` (lint/format/typecheck/test, unchanged
  from Band 12) gates `.github/workflows/cd.yml`, which builds and pushes
  `backend/` to `ghcr.io/<owner>/dealhunter-backend` on every green `main`
  build, tagged with both the commit sha and `latest`. `docker-
  compose.prod.yml` is the template for running that image (no
  cloud/server account is provisioned for this project yet — see "Known
  gaps" below).
- **Monitoring**: `GET /api/v1/health` (liveness, no dependencies), `GET
  /api/v1/ready` (readiness — checks Postgres + Redis, 503 if either is
  down), `GET /metrics` (Prometheus text format — request count + latency
  histogram by method/path template, `app/core/metrics.py`).
- **Scheduler**: the Band 07 marketplace ingestion scheduler
  (`AsyncIntervalScheduler`) finally has a call site —
  `app/bootstrap.py` builds it from `Settings` and `app/main.py`'s
  lifespan starts/stops it. Off by default (`SCHEDULER_ENABLED=false`);
  when enabled it needs `EBAY_CLIENT_ID`/`EBAY_CLIENT_SECRET` (or
  `KLEINANZEIGEN_PROVIDER_ENABLED=true`) to have any job to run, and is an
  in-process loop, not a distributed job queue — enable it in exactly one
  running instance per environment.
- **Dependency updates**: `.github/dependabot.yml` — weekly PRs for
  `backend/requirements.txt` and GitHub Actions versions. No `pub`
  (Flutter) entry yet, deliberately — see the file's own comment.

## Security (Band 14)

Full writeup — auth/JWT lifecycle, rate limiting, headers, secrets,
dependency scanning changelog — in [docs/security.md](docs/security.md).
Found a vulnerability? See [SECURITY.md](SECURITY.md) for how to report
it privately. Summary of what's new since Task #4's auth work:

- **Rate limiting**: Redis-backed fixed-window counter
  (`app/core/rate_limit.py`) on `POST /auth/{login,register,refresh}` —
  OWASP API4:2023. Off by default (`RATE_LIMIT_ENABLED=false`); see the
  module's own docstring for why default-on would break the existing
  integration suite.
- **Security headers**: `X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy`, `Permissions-Policy`, a `Content-Security-Policy` on
  every JSON response (exempting `/api/docs`/`/redoc`, which need their
  own CDN assets), `Strict-Transport-Security` when `APP_ENV=production`.
- **Opportunistic password rehashing**: `AuthService.login` upgrades a
  password hash created under outdated Argon2 parameters transparently on
  next login (`needs_rehash`, `UserRepositoryProtocol.
  update_password_hash` — deliberately separate from the generic
  `update()` to avoid ever clobbering `password_hash` with a stale value).
- **Dependency vulnerability scanning**: `pip-audit` runs in CI on every
  build. Fixed 4 packages with known CVEs (`python-jose`,
  `python-multipart`, `lxml`, `Pillow`); 3 more are deliberately deferred
  and documented (`starlette`/`pytest` need coordinated major-version
  bumps beyond this task's scope, `ecdsa` has no upstream fix and is never
  actually exercised by this app's HS256-only JWT usage) — see
  docs/security.md's "Dependency vulnerability scanning" section for the
  full reasoning per package.

## Analytics (Band 15)

Full writeup — event taxonomy, privacy, retention, KPIs — in
[docs/analytics.md](docs/analytics.md). Summary: `backend/app/modules/analytics/`
was a scaffold since Task #1 (entity, `AnalyticsCollectorProtocol`,
`analytics_events` table via the initial migration); Task #16 built the
repository, service, and REST surface (`POST/GET /api/v1/analytics/events`,
`GET /api/v1/analytics/summary`) on top of it. Validates event names
(lowercase snake_case) and rejects a denylist of PII-shaped property keys
(`email`, `password`, `access_token`, ...) rather than silently stripping
them. Two events are wired in automatically — `user_registered`
(`AuthService.register`) and `offer_favorited`/`offer_unfavorited`
(`FavoriteService`) — via the same optional, best-effort constructor-
injected pattern as everywhere else in this codebase (`analytics=None` by
default, a tracking failure never blocks the real action). Retention is a
manual script (`scripts/purge_analytics_events.py`), not an automatic job —
see the doc for why.

## AI Rules Framework (Band 16)

Full writeup — the five governing rules, confidence-handling policy,
prompt management — in [docs/ai_rules.md](docs/ai_rules.md). This is a
governance layer over DealBrain/RepairBrain/Vision AI (already built in
Tasks #6–#8), not a new feature: formalizes what those three were already
doing (explainable, honest-about-uncertainty, versioned, bounded,
reviewable weights) and closes two concrete gaps Task #17 found:

- **Model/prompt versioning**: `VisionObservation` now carries
  `cosmetic_model_used`/`cosmetic_prompt_version` — before this,
  `ANTHROPIC_VISION_MODEL` being operator-configurable meant two
  assessments months apart could have run against different Claude models
  with no way to tell afterward.
- **Bounded values as an entity invariant, not just an engine behavior**:
  new `app/core/ai_rules.py` (`validate_score`/`validate_confidence`) runs
  from `__post_init__` on every score/confidence-bearing entity
  (`DealScoreResult`, `AnalyzerOutput`, `RepairReport`,
  `CosmeticAssessment`, `VisionObservation`) — each one now refuses to be
  constructed outside its documented range, regardless of what code built
  it. `ScoringEngine`/`RepairScoringEngine` already clamped their own
  outputs; this is the backstop for every other way one of these entities
  could get built (a future analyzer, a bug, a test double).

## Status

See the 20 project tasks tracked for this build for current progress
(foundation → domain modules → API → mobile app → cross-cutting concerns).
All 20 are now complete — see [docs/roadmap.md](docs/roadmap.md) (Band 20)
for what comes after the MVP.
Known gaps carried over from the specification, tracked openly rather than
papered over with placeholders:

- **eBay Kleinanzeigen** has no official public API and its Terms of Service
  prohibit automated data collection. The provider built here respects
  `robots.txt` and rate limits and does **not** bypass bot detection or
  CAPTCHAs. Get legal sign-off before enabling it in production
  (`KLEINANZEIGEN_PROVIDER_ENABLED` defaults to `false`).
- **`FCM_PROJECT_ID`/`FCM_CREDENTIALS_JSON_PATH`** are needed for
  `FcmNotificationSender` to actually deliver pushes, and
  **`RESEND_API_KEY`/`RESEND_FROM_EMAIL`** for `ResendEmailSender` to
  deliver emails — until then, notifications are still created/listed/
  preferenced normally, just never delivered on that channel. Both fully
  tested against fakes/mocked HTTP (`tests/unit/test_fcm_provider.py`,
  `tests/unit/test_resend_provider.py`) but unverified against the live
  FCM/Resend APIs, same pattern as the eBay/Claude providers above.
  `AsyncIntervalScheduler`
  now does start from `app/main.py` (via `app/bootstrap.py`, Task #14) —
  but it's off by default (`SCHEDULER_ENABLED=false`) and, even enabled,
  produces no jobs without real `EBAY_CLIENT_ID`/`EBAY_CLIENT_SECRET` or
  `KLEINANZEIGEN_PROVIDER_ENABLED=true`, so the end of this chain (a real
  push notification firing off a real ingested offer) is still unverified
  against anything live — every link up to that point has test coverage,
  none of them against the real external services.
- **eBay developer credentials** are needed for `EbayApiProvider` to hit
  real endpoints — until then it's fully tested against mocked HTTP
  responses (`tests/unit/test_ebay_api_provider.py`) but unverified against
  the live API.
- **`ANTHROPIC_API_KEY`** is needed for `ClaudeCosmeticConditionAnalyzer` to
  hit the real Claude Vision API — until then it's fully tested against
  mocked HTTP responses (`tests/unit/test_claude_vision_provider.py`) but
  unverified against the live API, same pattern as the eBay provider above.
- Bands 11–15 and 17–20 were delivered as section skeletons rather than
  filled specifications; implementation follows established industry
  practice for those areas rather than a documented Deal Hunter AI–specific
  requirement.
- **`mobile/`** was written without a Flutter/Dart SDK available in this
  sandbox — every API call was checked against current package
  documentation, but none of it has run through `flutter pub get`/
  `analyze`/`test` yet, and no `android/`/`ios/` platform folders exist
  (needs `flutter create .` first). See `mobile/README.md`'s "Status"
  section for exact verification steps before building further on it.
- **Deployment (Band 13)** was written without a Docker daemon or a
  GitHub remote available in this sandbox: `backend/Dockerfile`,
  `docker-entrypoint.sh` and both compose files have never actually been
  built/run, and `.github/workflows/cd.yml` has never fired (it needs the
  CI workflow to complete successfully on a real `main` branch push first —
  see the workflow's own comment on why it's `workflow_run`-triggered, not
  `push`-triggered). No cloud/server account exists for this project yet,
  so `docker-compose.prod.yml` and `docs/deployment.md`'s release/rollback/
  backup process are a template and a runbook to follow, not something
  exercised end-to-end. Push this repo to GitHub and run
  `docker compose -f infra/docker/docker-compose.yml up --build` locally
  before trusting any of it further.
- **Security (Band 14)** rate-limit thresholds (10 logins/min, 5
  registers/hour, 30 refreshes/min) are informed guesses, not measured
  against real traffic — there is none yet. `starlette`/`pytest` have
  known CVEs deliberately left unpatched (need coordinated major-version
  bumps outside this task's scope) — see docs/security.md's "Dependency
  vulnerability scanning" section, which also lists which packages *were*
  bumped to close CVEs (`python-jose`, `python-multipart`, `lxml`, `Pillow`).
- **Analytics (Band 15)** has no BI/dashboard tool connected and no
  automatic retention job scheduled (the purge script exists, nothing
  calls it yet) — see docs/analytics.md's "Known gaps". Only 2 events are
  wired in automatically (`user_registered`, `offer_favorited`/
  `offer_unfavorited`); the rest of the taxonomy table there is documented
  candidates, not implemented yet.
