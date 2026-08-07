# Security (Band 14: Security)

Band 14's spec (`Band 14/Band_14_Security.md`) is a section-header
skeleton, not a filled specification (true of Bands 11–15 and 17–20 — see
the root [README.md](../README.md#status)) — everything below follows
OWASP's own guidance (the ASVS, the API Security Top 10) for a JSON API
backing a mobile app, not a documented Deal Hunter AI–specific requirement.

Most of the actual hardening work here (JWT lifecycle, Argon2, no-user-
enumeration on login, refresh-token rotation+revocation) was already built
in Task #4 and is only being documented, not changed, below — Task #15
(Band 14) adds what was still genuinely missing: rate limiting, secure
headers, opportunistic password rehashing, and dependency vulnerability
scanning.

## Authentication & JWT lifecycle

- Argon2id password hashing (`argon2-cffi`, library-recommended
  parameters — `app/core/security.py`). Never touches plaintext beyond the
  request that sets/verifies it.
- Access tokens (short-lived, `JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15` default)
  and refresh tokens (long-lived, `JWT_REFRESH_TOKEN_EXPIRE_DAYS=30`
  default), distinguished by a `type` claim `decode_token()` enforces — an
  access token can never be replayed as a refresh token or vice versa.
- Refresh tokens are **single-use and server-side revocable**: each one
  carries a `jti`, stored in `refresh_tokens` on issue
  (`AuthService._issue_token_pair`) and revoked the moment it's used to
  get a new pair (`AuthService.refresh`) — a stolen-and-replayed refresh
  token fails on its second use. Logout revokes on demand.
- **No user enumeration**: `AuthService.login` raises the same
  `UnauthorizedError("invalid email or password")` whether the email
  doesn't exist or the password is wrong — timing is not equalized (a
  missing user skips the Argon2 verify call entirely, which is measurably
  faster than a wrong-password path that runs it) — that's a known,
  accepted gap; closing it would mean spending Argon2 CPU time on every
  login attempt against nonexistent emails, a tradeoff not worth making
  without evidence this API is actually facing that specific timing attack.
- **Opportunistic password rehashing** (new in Task #15): on every
  successful login, `needs_rehash(user.password_hash)` checks whether the
  stored hash used outdated Argon2 parameters; if so, it's transparently
  upgraded using the plaintext password the login call already has (and
  is about to discard anyway) — `UserRepositoryProtocol.
  update_password_hash`, deliberately separate from the generic `update()`
  method so a profile-field update can never accidentally clobber
  `password_hash` with a stale value. Best-effort: a persistence failure
  here is logged, never blocks the login (`AuthService.login`).

## Authorization

`get_current_user_id` (`app/modules/auth/presentation/dependencies.py`)
gates every user-scoped endpoint; resource ownership is checked explicitly
per-module (e.g. search profiles return 404, not 403, on someone else's
profile — see `SearchService` — to avoid leaking existence). No role-based
access control exists yet beyond `User.is_admin`/`roles`, which nothing
currently branches on — there are no admin-only endpoints in this build.

## Rate limiting (new in Task #15)

`app/core/rate_limit.py` — a Redis-backed, fixed-window counter (`INCR` +
`EXPIRE` on a per-identifier-per-window key), applied via
`dependencies=[Depends(rate_limit(...))]` to the three unauthenticated auth
endpoints (OWASP API4:2023 "Unrestricted Resource Consumption" —
brute-force/credential-stuffing protection):

| Endpoint | Limit | Window |
| --- | --- | --- |
| `POST /api/v1/auth/login` | 10 | 60s |
| `POST /api/v1/auth/register` | 5 | 3600s |
| `POST /api/v1/auth/refresh` | 30 | 60s |

Identifies callers by client IP (there's no other stable identifier
available pre-authentication). **Off by default**
(`RATE_LIMIT_ENABLED=false`) — see `rate_limit.py`'s own module docstring
for why: the existing integration test suite calls `/auth/login`/
`/auth/register` dozens of times across test files sharing one Redis
instance and one synthetic client IP (httpx's `ASGITransport`), which would
trip a default-on limiter and fail unrelated tests. Enable it explicitly
per environment once that's actually wanted enforced — every non-auth
endpoint has no rate limiting at all yet, which is a real gap for a public
deployment (see "Known gaps").

## Security headers

`app/main.py`'s `security_headers_middleware` sets, on every response:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: geolocation=(), camera=(), microphone=(), payment=()`
- `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'` —
  on every response **except** `/api/docs`, `/redoc`, and
  `/docs/oauth2-redirect` (Swagger UI/Redoc load their own inline
  scripts/CDN assets; a strict CSP would break them). Every other response
  is pure JSON that's never meant to render as anything, so the strictest
  policy applies.
- `Strict-Transport-Security: max-age=63072000; includeSubDomains` — only
  when `Settings.is_production` is true. Sending HSTS over plain HTTP (true
  of every environment this app actually runs in today — see
  [docs/deployment.md](deployment.md)) would instruct browsers to force
  HTTPS for a host that might not have TLS termination yet, a
  self-inflicted outage. Inert until a real `production` deployment exists.

This is a JSON API consumed by the Flutter app, not a browser-rendered HTML
app — these headers mostly harden it against a browser ever being tricked
into treating a response as something it isn't, not the classic HTML/
inline-script XSS surface a server-rendered app would have.

## Secrets management

See [docs/deployment.md](deployment.md#secrets-management) for the full
writeup (local `.env`, CI's ephemeral inline secrets, CD's `GITHUB_TOKEN`,
production's `${VAR:?required}`-gated shell environment). Nothing sensitive
is ever committed — `.env` is gitignored, `.env.example` documents every
variable with placeholder/empty values only.

## Dependency vulnerability scanning (new in Task #15)

`.github/workflows/ci.yml` runs `pip-audit -r requirements.txt` on every
build (queries the OSV vulnerability database against exact pinned
versions). Running it against this project's pins on 2026-08-07 found 48
known vulnerabilities across 7 packages; fixed what could be safely bumped,
documented what couldn't:

**Fixed** (patch/minor bumps, or a major bump confirmed low-risk for how
this codebase actually uses the library — verified by re-running the full
fast test suite, `ruff`, and `mypy` after each):

- `python-jose` 3.3.0 → 3.5.0 (2 CVEs; also incidentally fixed a
  `datetime.utcnow()` deprecation warning that had been in the test output
  since it was first noticed).
- `python-multipart` 0.0.20 → 0.0.32 (6 CVEs; FastAPI only pins
  `>=0.0.7`, so this had a lot of room).
- `lxml` 5.3.0 → 6.1.0 (1 CVE; only ever used as a `BeautifulSoup` parser
  backend string in `kleinanzeigen.py` — no direct `lxml` API calls in this
  codebase to break).
- `Pillow` 11.1.0 → 12.3.0 (14 CVEs; only the stable, decades-old core API
  is used — `Image.open`/`ImageFilter`/`ImageStat`/`UnidentifiedImageError`
  in `vision/` — nothing exotic enough to have been removed across 3 major
  versions).

**Deliberately not fixed yet** (tracked, `--ignore-vuln`'d explicitly in
`ci.yml` with the same reasoning duplicated there so the gate's own comment
stays self-explanatory):

- **`starlette` 0.41.3** (7 CVE IDs) — fixed versions require FastAPI
  ≥0.116, a framework major-version bump. `fastapi`/`starlette` sit
  underneath every request this service handles; bumping them deserves a
  dedicated task with real regression testing (including against the
  integration suite's real Postgres/Redis, not just the fast unit suite),
  not a drive-by change inside a dependency-scanning sweep.
- **`pytest` 8.3.4** (1 CVE) — fixed in 9.x, which requires a coordinated
  bump of `pytest-asyncio` (confirmed via `pip install`: 0.25.0 hard-requires
  `pytest<9`) to its own 1.x line, and probably `pytest-cov` too. Dev/test-
  only dependency — never ships to production, so this is a lower-priority
  fix than anything in the first list, all of which are runtime
  dependencies.
- **`ecdsa` 0.19.2** (1 CVE, transitive via `python-jose[cryptography]`) —
  no fixed version exists upstream at all. This app signs JWTs with HS256
  (symmetric — see `.env.example`'s `JWT_ALGORITHM`) by default, so
  `ecdsa`'s EC-signing code path is present in the dependency tree but
  never actually executed by this codebase.

Re-run `pip-audit -r backend/requirements.txt` (without the `--ignore-vuln`
flags) periodically to check whether fixed versions have landed for the
three still-open items above.

## Known gaps

- **Rate limiting only covers the three auth endpoints**, and is off by
  default everywhere (see above). Every other endpoint (offers, search
  profiles, notifications, ...) has no rate limiting — fine for now (all
  of them require authentication, which is a much stronger gate than IP-
  based limiting), but worth revisiting if this becomes a genuinely public
  API with paying-customer SLAs to protect from noisy neighbors.
- **No secrets rotation policy** exists — `JWT_SECRET_KEY` rotation would
  invalidate every outstanding access/refresh token instantly (no
  key-versioning/`kid` claim support), which is a real operational gap for
  a production incident response plan (e.g. "the JWT secret leaked").
- **No CAPTCHA/bot-detection** on `/auth/register` — rate limiting is the
  only defense against automated account creation, and it's off by default.
- **No admin/RBAC surface** — `User.is_admin`/`roles` exist in the schema
  but nothing in this codebase currently checks them; there's no
  admin-only functionality to protect yet.
- **`starlette`/`pytest` version bumps deferred** — see "Dependency
  vulnerability scanning" above.
- Nothing here has been exercised against a real production deployment —
  see [docs/deployment.md](deployment.md)'s own "Known gaps": no cloud/
  server account, no real TLS termination to verify HSTS against, no real
  traffic pattern to validate the rate-limit thresholds chosen above
  against (10 logins/min, 5 registers/hour, 30 refreshes/min are informed
  guesses, not measured).
