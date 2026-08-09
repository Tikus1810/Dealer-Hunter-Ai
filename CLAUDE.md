# Claude Context — Deal Hunter AI

This file is Band 17's deliverable (`Band 17/Band_17_Claude_Context.md`):
the shared context, coding standards, architecture conventions, naming
rules and repository guidelines Claude Code (or any contributor) should
follow when working in this repo. It documents conventions that were
**already in continuous use** across Tasks #1–#17 — this is the write-up,
not a new policy.

## What this project is

An app that discovers, scores (**DealBrain**) and repair-analyzes
(**RepairBrain**) second-hand tech (Windows laptops, MacBooks, iPhones,
game consoles), with a Vision AI cosmetic-condition check and push
notifications for saved searches. Backend: FastAPI/Python 3.13. Mobile:
Flutter/Riverpod/go_router. Postgres + Redis, Docker Compose, GitHub
Actions CI/CD.

Specs live in `Band 1/` … `Band 20/` (original input, kept as-is for
traceability — **never edit them**). Bands 1–10 and 16 are fully
specified; Bands 11–15 and 17–20 are section-header skeletons with no
filled content — for those, standard industry practice was followed
instead of a literal spec, and that's called out explicitly wherever it
applies (e.g. DealBrain's v1 scoring weights, RepairBrain's part-price
catalog).

## Architecture

### Backend: modular monolith, Clean Architecture

One folder per bounded context under `backend/app/modules/`: `auth`,
`users`, `offers`, `search`, `scoring` (DealBrain), `repair`
(RepairBrain), `vision`, `notifications`, `analytics`. Each module is
layered:

```
modules/<name>/
  domain/            entities — no framework/DB dependency, pure Python
  application/        use cases + the module's public interface
                       (Protocol classes in interfaces.py)
  infrastructure/      SQLAlchemy repos, external providers, adapters
  presentation/         FastAPI routers + Pydantic DTOs
```

**Module boundary rule**: other modules and the API layer may only depend
on a module's `application/interfaces.py` — never reach into its
`infrastructure/` or `domain/` directly. Cross-cutting concerns (e.g.
notifications reacting to a new offer) are wired through protocol-typed
extension points passed in at composition time (`app/bootstrap.py`), not
direct imports between modules — see `OfferPersistedHookProtocol` /
`SavedSearchMatchNotifier` for the reference example.

Composition root: `app/bootstrap.py` builds and wires everything
(scheduler, hooks, senders) from `Settings`; `app/main.py`'s lifespan
starts/stops what needs a lifecycle.

### Mobile: feature-first Clean Architecture

`mobile/lib/features/<name>/{domain,data,presentation}`, same
layering intent as the backend (domain has no Flutter/http dependency,
data implements repositories, presentation holds widgets + Riverpod
controllers). `core/` holds cross-feature pieces: `core/network`
(Dio + interceptors), `core/theme`, `core/error`, `core/router`.
No code generation — `fromJson`/`toJson` are hand-written.

### Extension points (the seams new features plug into)

- `OfferPersistedHookProtocol` (offers module) — react to a newly
  ingested offer without `offers` importing the reacting module.
- `AnalyticsCollectorProtocol` — optional constructor-injected,
  best-effort (`analytics: AnalyticsCollectorProtocol | None = None`);
  every existing call site keeps working unchanged when a new emitter is
  added, because the param defaults to `None`.
- `NotificationSenderProtocol` per channel (only `FcmNotificationSender`/
  PUSH is implemented; EMAIL is modeled but not sent — a real gap,
  documented, not silent).
- Score/confidence-bearing entities all run through `app/core/ai_rules.py`
  (`validate_score`/`validate_confidence`) from `__post_init__` — any new
  analyzer output gets this backstop for free by using the existing base
  patterns, not by remembering to call it manually.

## Naming conventions

- **Python**: modules/files/functions/variables `snake_case`, classes
  `PascalCase`, Protocol interfaces suffixed `Protocol`
  (`OfferRepositoryProtocol`), constants `UPPER_SNAKE_CASE`. Test files
  mirror the module under test (`tests/unit/modules/offers/test_offer_
  repository.py`).
- **Dart**: files `snake_case.dart`, classes `PascalCase`, Riverpod
  providers `camelCase` ending in `Provider`, controllers suffixed
  `Controller`.
- **Analytics event names**: `snake_case`, validated against
  `domain/taxonomy.py`'s `AnalyticsEventName` enum — no ad-hoc string
  literals in new call sites.
- **DB migrations**: Alembic revision *files* prefixed `NNNN_short_
  description` (`0002_notification_device_tokens_and_preferences.py`) —
  but the internal `revision`/`down_revision` id strings stay short
  (`"0001"`, `"0002"`, ...), not the full filename. Found the hard way in
  a later review pass: Alembic's `alembic_version.version_num` column
  defaults to `VARCHAR(32)`, and a full descriptive filename as the id
  overflows it the first time a real `alembic upgrade head` actually
  runs — never caught by this project's integration tests, which build
  the schema straight from `Base.metadata.create_all` and never invoke
  Alembic at all (see `tests/integration/conftest.py`).
- **REST routes**: `/api/v1/<module-plural-or-verb>`, auth-required
  unless explicitly a health/readiness/docs endpoint.

## Coding standards / quality gates

Backend (`backend/`, enforced in CI — see `.github/workflows/ci.yml`):
- `ruff check .` and `ruff format --check .` (line length 100, rules
  `E, F, I, UP, B, SIM`; FastAPI's `Depends(...)`-as-default is
  explicitly exempted from B008 — see `pyproject.toml`).
- `mypy app scripts tests --strict`.
- `pytest -m "not integration"` (fast, no services) locally before every
  commit; full suite (needs Postgres+Redis) runs in CI. Coverage gate:
  80%.
- `pip-audit` every CI run, with a documented `--ignore-vuln` list in
  `docs/security.md` for the 3 known, currently-unfixable CVEs.

Mobile (`mobile/`, `analysis_options.yaml`): `flutter_lints`, plus
project rules `prefer_single_quotes`, `prefer_const_constructors`,
`require_trailing_commas`, `unnecessary_lambdas`, and strict
analyzer options (`strict-casts`, `strict-inference`, `strict-raw-
types`). Run `flutter analyze` and `flutter test` before committing —
this project's own history includes a real bug (`flutter analyze`'s
first-ever CI run caught a non-exhaustive `DioExceptionType` switch)
that unit tests alone would not have caught.

General: **no placeholder code** in a shipped task — if something is
genuinely a stand-in (DealBrain's v1 weights, RepairBrain's part-price
catalog, mobile's design tokens before Task #19), it's a real, working
implementation flagged in a comment/doc as tunable, not a stub.

## Testing conventions (Band 12, `docs/README.md`'s "Tests" section)

- `tests/unit/` — fakes for every port, no DB/network,
  no `@pytest.mark.integration`. This is what runs in any sandbox
  without Postgres available.
- `tests/integration/` — real HTTP requests against the actual FastAPI
  app, or direct repository tests, against a real (now CI-shared, not
  exclusively owned) Postgres instance. **Any new integration test that
  inserts shared/reference data (categories, well-known event names)
  must be idempotent or use a randomized identifier** — the first real
  CI run surfaced multiple `UniqueViolationError`s and cross-test
  assertion breakage from tests that assumed exclusive table ownership;
  see the fix pattern in `backend/tests/integration/conftest.py`'s
  `seeded_category` fixture (`select`-then-insert-if-missing) and
  `test_analytics_repository.py`'s `_unique_event_name()`.

## Commit conventions

One commit per completed task/Band, imperative summary line naming the
Band/feature (`"Analytics-Subsystem: event tracking, taxonomy, privacy,
retention (Band 15)"`), German is acceptable in the summary word choice
where it reads more naturally (`"Security-Härtung"`) since this is a
German-market product, but code/comments/docs stay in English. Fix
commits after a CI run are numbered explicitly ("Fix first real CI
failures: ...", "Fix second round of real CI failures: ...") so the
sequence of what broke and in what order stays traceable in `git log`.

## Working conventions for Claude Code in this repo

- Check `TaskList` first before assuming where the build sequence left
  off — work may have continued in a later session than the one that
  wrote a given memory note.
- Prefer a real tool's own error output over external API-sourced
  documentation when they conflict (e.g. `flutter pub get`'s suggested
  version fix over pub.dev's per-version metadata, which was wrong once
  already in this project's history).
- When a spec Band is an unfilled skeleton (11–15, 17–20), say so
  explicitly in the commit/doc rather than silently inventing a spec —
  follow standard industry practice and flag the deviation.
- Anything genuinely unverifiable in the current environment (no
  Flutter/Docker/Postgres/live API keys available) gets stated as a
  caveat, not silently assumed to work — this project's actual first
  real CI run (2026-08-07) found real bugs across pytest-asyncio config,
  a missing runtime dependency, Flutter SDK/package version pins, and a
  GHCR image-tag casing bug, all previously invisible specifically
  because nothing had run for real yet.
