# Future Features Roadmap (Band 20)

Band 20's spec (`Band 20/Band_20_Future_Features_Roadmap.md`) is a
section-header skeleton, not a filled specification (true of Bands
11–15 and 17–20 — see the root [README.md](../README.md#status)). This
document fills in its "Required Sections" list with a prioritized,
architecture-grounded roadmap for what comes after the Band 1 MVP
(all of which is now built — see [README.md](../README.md#status)).

## Vision

Deal Hunter AI's MVP (Bands 1–19) proved the core loop: ingest offers,
score them explainably (DealBrain), estimate repair economics
(RepairBrain), flag cosmetic condition (Vision AI), and notify on
matches. Everything below extends that loop — more device categories,
more surfaces, more automation-assist — without ever crossing Band 1's
explicit MVP boundary: **no automatic purchasing, no messaging sellers,
no circumventing marketplace restrictions**. That boundary is a
permanent constraint on this roadmap, not just an MVP-era limitation —
every item below was checked against it.

## Objectives

- Give a concrete, buildable next step for each of Band 20's Purpose-
  listed themes (device categories, AI enhancements, web platform,
  browser extension, collaborative features, enterprise edition, plugin
  architecture, i18n, scalability, release planning) — not just name
  them.
- Point every roadmap item at the actual extension seam it would use in
  the current codebase, so "modular architecture" (Band 1, Core
  Principle 3) is demonstrated, not just asserted.
- Sequence by dependency and risk, not by theme — e.g. i18n blocks a
  real web platform launch (German-only notification copy today, see
  `docs/analytics.md`), so it's phased earlier than the theme list's
  ordering would suggest.

## Architecture Impact

No code changes in this Band — this is the planning document Band 20
asks for. Every item below is deliberately scoped to land through an
**existing** extension point rather than requiring a new architectural
seam, which is itself validation that Band 2's module-boundary design
(depend on `application/interfaces.py` only) and the Protocol-based
extension points introduced across Tasks #9/#10/#16 (`OfferPersistedHookProtocol`,
`NotificationSenderProtocol` per channel, `AnalyticsCollectorProtocol`)
generalize to unplanned future work, not just the features they were
originally built for.

## Functional Requirements — prioritized phases

### Phase 1 — near-term, extends existing modules (no new bounded context)

1. **Additional device categories** (tablets, smartwatches, desktop
   PCs). Seam: `OfferCategory` (`backend/app/modules/offers/domain/
   entities.py`) is a closed `StrEnum` today (`WINDOWS_LAPTOP`,
   `MACBOOK`, `IPHONE`, `GAME_CONSOLE`) — adding a value plus a matching
   `DealBrain`/`RepairBrain` analyzer profile
   (`domain/catalog.py`-equivalent per module) is additive, no
   migration of existing data. Real work is per-category: what "good
   condition" and "common faults" mean differs enough (a laptop's
   battery-cycle count vs. a game console's disc-drive noise) that this
   is N small research+content tasks, not one generic one.
2. ~~**EMAIL notification channel**~~ — **done** (post-MVP review pass,
   2026-08-09): `ResendEmailSender` implements `EmailSenderProtocol`,
   wired the same optional/best-effort way as FCM. Kept here struck
   through rather than deleted, as a record that this roadmap is a living
   document, not a fixed backlog.
3. **Automatic retention job** for analytics purge — `scripts/
   purge_analytics_events.py` (Task #16) exists and is manual; wiring it
   into `AsyncIntervalScheduler` (the same scheduler Band 07/Task #14
   already runs ingestion jobs through) is additive, no new
   infrastructure.

### Phase 2 — mid-term, new bounded contexts following the established module shape

4. **AI enhancements**: multi-photo cross-referencing for Vision AI
   (Task #8 currently scores one photo set per assessment, not
   photo-vs-listing-description consistency); a DealBrain "price
   trend" analyzer using historical `Offer` rows already persisted
   (Task #3's schema) instead of only the current snapshot. Both are
   new `AnalyzerProtocol` implementations plugged into the existing
   `ScoringEngine` (Task #6) — no new module.
5. **Collaborative features** (shared search profiles, "deal of the
   week" digest emails). New bounded context
   `modules/collaboration/` following the four-layer shape every other
   module uses; reads `search`/`offers` only through their
   `application/interfaces.py`, per Band 2's boundary rule — never a
   direct join into their tables.
6. **Browser extension** ("show Deal Score for this eBay listing while
   browsing"). Pure API consumer — no backend changes beyond exposing
   what `GET /api/v1/offers/{id}/deal-score` already returns; the work
   is entirely a new, separate client (Manifest V3 extension calling
   the existing REST API with the user's existing JWT), same relationship
   the Flutter app already has to the backend.

### Phase 3 — long-term, cross-cutting or platform-level

7. **Internationalization**: today's notification templates
   (`domain/templates.py`, Task #10) and every UI string in `mobile/`
   are hardcoded German literals — a deliberate MVP scope choice (this
   product's actual market), not an oversight, but it means i18n is a
   real refactor (extract every literal to a resource/ARB file), not a
   config flag. Sequenced before web platform below because a public
   web surface is far more likely to draw non-DACH traffic than the
   mobile app has so far.
8. **Web platform**: a browser-based client, same "consumes the
   existing REST API" relationship as the Flutter app and the browser
   extension (item 6) — the API-first principle (Band 1, Core Principle
   4) is what makes this additive rather than a backend rewrite. Blocked
   on item 7 in practice, not in architecture.
9. **Plugin architecture**: formalizing the pattern that already exists
   informally (`OfferPersistedHookProtocol`, `AnalyticsCollectorProtocol`,
   per-channel `NotificationSenderProtocol`) into a documented,
   third-party-implementable interface — e.g. a `MarketplaceProviderProtocol`
   plugin surface so a future marketplace beyond eBay/Kleinanzeigen
   (Task #5) doesn't require a core-team PR. Explicitly the last item
   in this phase: formalizing an interface before it has 3+ real
   implementations tends to guess the wrong abstraction.
10. **Enterprise edition** (multi-tenant, team accounts, audit
    exports). The biggest architectural change on this list — today's
    schema (Task #3) is single-tenant by design (a `user_id` foreign
    key, not a `tenant_id`), so this needs a deliberate migration
    strategy (additive `tenant_id` columns + row-level scoping), not
    just new endpoints. Flagged as the highest-risk item for that
    reason.

### Scalability milestones (cross-cutting, not a phase)

- Current bottleneck-by-design: `AsyncIntervalScheduler` (Task #14) runs
  in-process with the API server, single-instance only (documented in
  `docker-entrypoint.sh`'s migrate-on-startup caveat, same single-
  instance assumption). Horizontal scaling of the API server needs the
  scheduler split out to its own worker process first — a prerequisite
  for Phase 2 item 3 running reliably at more than one replica, and for
  Phase 3 generally.
- Redis is currently used only for JWT refresh-token/rate-limit state
  (Tasks #4/#15) — a queue-backed job system (e.g. the scheduler
  publishing jobs Redis-side for worker processes to consume) is the
  natural next step once the single-instance scheduler above is split
  out, not a separate initiative.

## Non-Functional Requirements

- Every phase above must preserve Band 2's module-boundary rule
  (`application/interfaces.py` only) — a roadmap item that requires
  reaching into another module's `infrastructure/` is a sign the item
  needs its own new extension point, not that the rule should bend.
- Every phase above must preserve Band 1's "Not included" boundary
  (no automatic purchasing, no seller messaging, no marketplace-restriction
  circumvention) — checked explicitly per item above, not assumed.
- New bounded contexts (Phase 2/3) follow the same layering, testing
  (`tests/unit` + `tests/integration` split, Task #13), and CI quality
  gates (ruff/mypy/pytest/coverage-80%) as every existing module — see
  [CLAUDE.md](../CLAUDE.md).

## Standards

Same as the rest of the codebase — Clean Architecture, SOLID, the
naming/testing/commit conventions in [CLAUDE.md](../CLAUDE.md) (Band 17).
No new standards introduced by this Band.

## Risks

- **Enterprise edition (item 10)** is a real schema migration, not just
  new code — needs a dedicated design pass (and likely a paying-customer
  commitment) before starting, not something to build speculatively.
- **i18n (item 7)** is undersized if treated as "add a translation
  file" — every hardcoded German string across `backend/app/modules/
  notifications/domain/templates.py` and `mobile/lib/features/*` needs
  finding and extracting first.
- **Plugin architecture (item 9)** risks over-abstracting: this
  codebase's own history (CLAUDE.md's "no undocumented assumptions"
  rule) argues for waiting until there are ≥2 real third-party-style
  implementations of a seam before formalizing its public contract.
- This roadmap itself is a single-session planning pass, not validated
  against real user demand signals (no production users yet — see
  README.md's "Status") — priorities here should be revisited once
  `docs/analytics.md`'s event data actually has volume behind it.

## Acceptance Criteria

- [x] Every Band-20-Purpose theme (device categories, AI enhancements,
      web platform, browser extension, collaborative features,
      enterprise edition, plugin architecture, i18n, scalability,
      release planning) has a corresponding, concretely-scoped item
      above.
- [x] Every item names the specific existing extension point/interface
      it would use, or explicitly flags that none exists yet (items 5,
      9, 10).
- [x] Phasing reflects actual dependency order (i18n before web
      platform; scheduler split before horizontal scaling), not just
      the spec's listing order.
- [x] No item conflicts with Band 1's MVP exclusions.

## Definition of Done

This document merged and linked from the root README — planning-only
Bands (17, 19, 20) don't have a "shipped code" done-condition the way
Bands 1–16/18 do. Re-review this roadmap's priority order at the next
major milestone (first real production users / first real analytics
volume), not on a fixed calendar.

## Future Extension Points

The roadmap *is* the future-extension-points list (Functional
Requirements above) — restated in interface terms for whoever picks up
a given item:

| Future item | Extension point | Status |
|---|---|---|
| New device category | `OfferCategory` enum + per-module analyzer profile | Interface exists |
| EMAIL notifications | `EmailSenderProtocol` (`ResendEmailSender`) | Done (2026-08-09) |
| Analytics retention job | `AsyncIntervalScheduler` job registration | Interface exists |
| New DealBrain/RepairBrain analyzers | `AnalyzerProtocol` → `ScoringEngine` | Interface exists |
| Collaboration features | New `modules/collaboration/` bounded context | Needs new module |
| Browser extension / web platform | Existing REST API (`/api/v1/...`) | Interface exists |
| New marketplace provider | `MarketplaceProviderProtocol` (Band 07) | Interface exists |
| Formal plugin architecture | Generalizing the above Protocols into a documented external contract | Not started — see Risks |
| Multi-tenancy | New `tenant_id`-scoped schema | Needs migration design |

## Review checklist

- [x] Grounded in code that exists today (file paths/Protocol names
      checked against the actual repo, not asserted from memory).
- [x] Respects Band 1's MVP exclusions explicitly, item by item.
- [x] Sequenced by real dependency, with the reasoning stated, not just
      asserted.

## Traceability to Band 01

Every phase above is a continuation of Band 1's Core Principles: Phase 1
extends **Explainable AI** (more categories/analyzers) without touching
**Human decision remains final**; Phase 2's browser extension and Phase
3's web platform are direct expressions of **API-first** (Core Principle
4); the module-boundary discipline required of every new bounded
context throughout is **Modular Architecture** (Core Principle 3) and
**Security by Design**/**Test-first Development** apply unchanged (Core
Principles 5–6, enforced by the same CI gates as everything already
shipped).
