# Analytics (Band 15)

Band 15's spec (`Band 15/Band_15_Analytics.md`) is a section-header
skeleton, not a filled specification (true of Bands 11–15 and 17–20 — see
the root [README.md](../README.md#status)) — everything below follows
standard first-party product-analytics practice, not a documented Deal
Hunter AI–specific requirement.

The module (`backend/app/modules/analytics/`) existed as a scaffold since
Task #1 (domain entity, `AnalyticsCollectorProtocol`, the SQLAlchemy model
and its table via the initial migration) but had no repository, service,
router, or automatic event emission until Task #16.

## Architecture

Same four-layer module shape as everything else (`domain/` → pure entities
and the taxonomy; `application/` → `AnalyticsService` + the two Protocols
other modules and the router depend on; `infrastructure/` →
`SqlAlchemyAnalyticsEventRepository`; `presentation/` → REST endpoints).

`AnalyticsCollectorProtocol` (`application/interfaces.py`) is the
cross-module extension point — the same pattern as `notifications`'
`NotificationServiceProtocol` and `offers`' `OfferPersistedHookProtocol`:
any module can depend on `analytics.application.interfaces` and call
`.track(...)` without knowing anything about how or where events are
stored (Band 2's module-boundary rule: depend on `application/interfaces.py`
only, never `infrastructure/`).

## Event taxonomy

`domain/taxonomy.py` defines:

- **Shape rules** every event name must satisfy regardless of source:
  lowercase `snake_case`, 2–120 characters
  (`is_valid_event_name`/`MAX_EVENT_NAME_LENGTH`).
- **`AnalyticsEventName`** — the enum of event names *this backend itself*
  emits automatically (see "Automatic (first-party) events" below). Not an
  allowlist: `POST /api/v1/analytics/events` also accepts client-driven
  names (Flutter screen views, button taps, ...) that aren't in this enum,
  validated only against the shape rules, not this specific set. One
  canonical spelling for the handful of events the backend emits itself is
  the point, not a closed universe of valid names.

| Event | Emitted from | Properties |
| --- | --- | --- |
| `user_registered` | `AuthService.register` | *(none)* |
| `offer_favorited` | `FavoriteService.add_favorite` | `offer_id`, `category` |
| `offer_unfavorited` | `FavoriteService.remove_favorite` | `offer_id` |
| *(anything else)* | Flutter app, via `POST /analytics/events` | client-defined |

## Privacy

- **Auth required** on every endpoint, including `POST /events` — no
  anonymous ingestion in v1 (see `presentation/router.py`'s module
  docstring for why: nowhere useful to attribute a logged-out event to
  yet, and an open POST endpoint with no caller identity is an abuse
  magnet). `user_id` always comes from the JWT, never the request body — a
  client cannot attribute an event to someone else.
- **Denylisted property keys** (`DENYLISTED_PROPERTY_KEYS`): `email`,
  `password`/`password_hash`, `phone`/`phone_number`, `ssn`,
  `credit_card`/`card_number`/`cvv`, `access_token`/`refresh_token`/`jwt`/
  `authorization`. `AnalyticsService.track()` raises `ValidationError`
  (422) rather than silently stripping the field — the caller finds out
  immediately instead of assuming the data was recorded. **Defense in
  depth, not a guarantee**: this catches the obvious mistakes in a fixed
  list of key names; it is not content-inspection of values, and it is not
  a substitute for the client (the Flutter app) simply never sending PII
  as an analytics property in the first place.
- **Property shape is restricted to JSON primitives**
  (`str | int | float | bool | None` — see `presentation/schemas.py`'s
  `PropertyValue`), max 25 properties per event, string values capped at
  500 characters. No nested objects/arrays — keeps properties genuinely
  flat/queryable and, as a side effect, makes it harder to smuggle
  arbitrarily-structured data past the denylist above.
- **`ON DELETE SET NULL`** on `analytics_events.user_id` (see the initial
  migration): deleting a user account doesn't cascade-delete their event
  history, it anonymizes it — aggregate counts stay accurate, but the
  events are no longer attributable to anyone. No explicit "export/delete
  my data" flow exists yet for a GDPR-style data subject request; this is
  the one piece of that story that's already in place by construction.

## Retention

No automatic deletion job runs (Band 15: "retention" is a requirement,
"automatically enforced" is not — see `scripts/purge_analytics_events.py`'s
own docstring for the reasoning). `AnalyticsService.purge_events_older_than(days)`
does the actual deletion; run it manually or wire it into a cron/scheduled
job once this is a real deployment:

```bash
python -m scripts.purge_analytics_events --days 180  # 180 is also the default
```

180 days is a starting point, not a measured/compliance-driven number —
revisit once there's a real retention policy to satisfy.

## KPIs / aggregation

v1 ships exactly two aggregate numbers per event name
(`GET /api/v1/analytics/summary?event_name=...&since_days=...`,
`AnalyticsSummary`): **count** (total volume) and **distinct_users**
(reach, excluding anonymous events — `NULL` `user_id` never counts toward
it). Every other KPI a v1 product-analytics setup usually wants (daily
active users, funnel conversion, retention cohorts) is a derived query on
top of these two numbers and the raw `analytics_events` table, not
something this module computes yet — deliberately minimal rather than
guessing at KPIs nobody has asked for.

## Dashboards

None exist — no BI/dashboarding tool (Metabase, Grafana, Looker, ...) is
provisioned for this project (see "Known gaps"). `GET /api/v1/analytics/summary`
and `GET /api/v1/analytics/events/{event_name}` are meant to be either
called directly by an internal tool later, or to have a read replica /
export job point a real BI tool at the `analytics_events` table directly —
whichever fits once there's an actual dashboard consumer to build for.

## Future extension points

- A `properties` JSONB GIN index isn't in the initial migration — add one
  if/when querying by property value (not just event name) becomes a real
  need; premature before there's a real query pattern to optimize for.
- Batched/async ingestion (a queue in front of `AnalyticsService.track`)
  if event volume ever makes synchronous per-request writes a bottleneck —
  not needed at today's scale.
- Session/funnel analysis needs a `session_id` concept this schema doesn't
  have yet (`AnalyticsEvent` has no session grouping key).

## Known gaps

- No BI/dashboard tool connected — see "Dashboards" above.
- No automatic retention enforcement — see "Retention" above (the
  mechanism exists, nothing schedules it).
- No admin-only restriction on `GET /summary`/`GET /events/{name}` — any
  authenticated user can query aggregate counts for any event name right
  now (same "no RBAC surface yet" gap noted in
  [docs/security.md](security.md#known-gaps)). Low risk today (nothing
  here is per-user-identifiable through the summary endpoint), worth
  revisiting once real usage data exists that competitors/users shouldn't see.
- Automatic (first-party) event coverage is intentionally small (2 events)
  — `offer_viewed`, `deal_score_viewed`, `repair_report_generated`,
  `search_profile_created`, `notification_opened` are documented as
  candidates in the table above's spirit but not wired in; add them the
  same way `offer_favorited`/`user_registered` were (an optional
  `analytics: AnalyticsCollectorProtocol | None = None` constructor
  parameter, best-effort, never blocking the real action) once there's a
  concrete question those events would answer.
