# Deal Hunter AI

Production-grade AI platform that discovers, evaluates and prioritizes
second-hand technology deals (Windows laptops, MacBooks, iPhones, game
consoles) — explainable Deal Score, repair economics, and push
notifications for saved searches.

Specification source: `Band 1/` … `Band 20/` (see [Band 1](Band%201/Band_01_Master_PRD.md)
for the master PRD). Each `Band N/` folder is the original spec input and is
kept as-is for traceability; this repo implements it incrementally.

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

Health check: `GET http://localhost:8000/api/v1/health`
API docs: `http://localhost:8000/api/docs`

## Tests

```bash
cd backend
pytest -m "not integration"   # unit tests only, no services required
pytest                        # full suite — needs Postgres running (see docker-compose above)
```

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
best-effort pushes via FCM), and `FcmNotificationSender`
(`infrastructure/fcm_provider.py`, wraps `firebase_admin.messaging.send` in
`asyncio.to_thread` since the SDK has no native async support).

**Event routing:** `SavedSearchMatchNotifier`
(`application/match_notifier.py`) implements `OfferPersistedHookProtocol`
(`app/modules/offers/application/interfaces.py`) — the "Trigger Analysis"
extension point `IngestionService` always had. When wired in (see
`AsyncIntervalScheduler`'s `on_offer_persisted` param), every newly
persisted offer is matched against active saved searches
(`SearchService.match_offer_against_profiles`) and each match becomes a
notification, without the `offers` module ever importing `notifications`
or `search` directly — the hook is a `Protocol` the composition root
satisfies with a concrete implementation (Band 2 module-boundary rule).

REST surface: `POST`/`DELETE /api/v1/notifications/devices` (register/
unregister an FCM device token), `GET /api/v1/notifications` (paginated
inbox), `POST /api/v1/notifications/{id}/read`, `GET`/`PUT
/api/v1/notifications/preferences`. All user-scoped, all require auth.

**Only PUSH is actually delivered in v1** — Band 11 lists EMAIL as a
channel too, but this task's scope was FCM specifically. An EMAIL-channel
notification is still recorded (satisfying the audit-log requirement),
just not sent anywhere yet; that's a documented gap, not a silent one.

Without `FCM_PROJECT_ID`/`FCM_CREDENTIALS_JSON_PATH` set, notifications
still work end-to-end (persisted, listed, marked read, preferences) — push
delivery is just skipped, same pattern as the other optional providers.

## Flutter App (Band 4 / Band 18)

`mobile/` implements Band 4 end-to-end: feature-first Clean Architecture,
Riverpod 2.x state management, go_router navigation (auth-gated), a
Material 3 light/dark design system built from token files, and every
Band 4 "Core Feature" with real UI wired against the real backend API —
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

## Status

See the 20 project tasks tracked for this build for current progress
(foundation → domain modules → API → mobile app → cross-cutting concerns).
Known gaps carried over from the specification, tracked openly rather than
papered over with placeholders:

- **eBay Kleinanzeigen** has no official public API and its Terms of Service
  prohibit automated data collection. The provider built here respects
  `robots.txt` and rate limits and does **not** bypass bot detection or
  CAPTCHAs. Get legal sign-off before enabling it in production
  (`KLEINANZEIGEN_PROVIDER_ENABLED` defaults to `false`).
- **`FCM_PROJECT_ID`/`FCM_CREDENTIALS_JSON_PATH`** are needed for
  `FcmNotificationSender` to actually deliver pushes — until then,
  notifications are still created/listed/preferenced normally, just never
  pushed to a device. Fully tested against a fake `send_fn` seam
  (`tests/unit/test_fcm_provider.py`) but unverified against the live FCM
  API, same pattern as the eBay/Claude providers above. The scheduler that
  would trigger ingestion (and therefore saved-search-match notifications)
  in production also isn't started anywhere yet — `AsyncIntervalScheduler`
  exists and is tested, but nothing calls `.start()` from `app/main.py`,
  same as before this task (real provider/job configuration is a
  Task #14/Deployment concern, not a Task #10 one).
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
