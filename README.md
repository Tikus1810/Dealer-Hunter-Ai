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
pytest
```

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
- **Firebase Cloud Messaging** (notifications) requires a real Firebase
  project + service account credentials, supplied by the project owner.
- Bands 11–15 and 17–20 were delivered as section skeletons rather than
  filled specifications; implementation follows established industry
  practice for those areas rather than a documented Deal Hunter AI–specific
  requirement.
