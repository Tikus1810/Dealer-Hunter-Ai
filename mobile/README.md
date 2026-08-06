# Deal Hunter AI — Flutter App

Flutter client for [Deal Hunter AI](../README.md), implementing
[Band 4](../Band%204/Band_04_Flutter.md) (Flutter Application) and
[Band 18](../Band%2018/Band_18_UI_UX_Design_System.md) (UI/UX Design
System — a template band, see the root README's "Known gaps").

## Status: foundation (Task #11)

This is the app **skeleton**: Clean Architecture layering, Riverpod DI,
go_router navigation with every Band 4 "Core Feature" reachable, a Material
3 light/dark design system, and a fully working Authentication vertical
slice (register/login/logout/token-refresh) wired end-to-end against the
real backend API. Every other feature (Dashboard content, Search Profiles,
Offer List/Details, Deal/Repair Analysis, Favorites, Notifications,
Settings) is a placeholder screen — real UI for those is **Task #12**
("Flutter Core-Screens").

**Not yet verified against a real Flutter SDK.** This sandbox has no
Flutter/Dart toolchain installed, so none of this has been run through
`flutter pub get`, `flutter analyze`, or `flutter test`. Every API call
(Riverpod 2.x, go_router, Dio, flutter_secure_storage) was checked against
current package documentation while writing it, but that's not a
substitute for the real analyzer/compiler. Treat this the same way you'd
treat any other unreviewed diff — just one this project's other modules
didn't need to be, because Python/pytest/mypy/ruff could all run locally
in that sandbox.

Only the Dart source tree (`lib/`, `test/`, `pubspec.yaml`,
`analysis_options.yaml`) was delivered — no `android/`/`ios/`/`web/`
platform folders exist yet, since generating those needs the Flutter SDK.
**Before building on this, please run, in order:**

```bash
cd mobile
flutter create --project-name deal_hunter_ai .   # adds platform folders; should not
                                                   # touch existing lib/ or pubspec.yaml
                                                   # content, but review `git diff` after
flutter pub get
flutter analyze
flutter test
```

...and report back (or fix) whatever that surfaces. `.github/workflows/
ci.yml` already has a `flutter` job (from Task #1) that runs exactly this
sequence — pushing this branch will exercise it for real even before
anyone runs it locally, `flutter-version: "3.27.0"`.

## Architecture

Feature-first + Clean Architecture (Band 4), matching the backend's own
layering philosophy:

```
lib/
  core/                    cross-cutting: DI, network, router, theme, widgets
    config/                AppConfig (API base URL, from --dart-define)
    di/                    top-level Riverpod providers
    error/                 AppException + ErrorMapper (backend's
                           ErrorResponse{code,message,details,correlation_id}
                           becomes one typed exception every screen understands)
    network/               Dio + AuthInterceptor (auto token refresh) +
                           RetryInterceptor (transient-failure retry) +
                           TokenStorage (flutter_secure_storage)
    router/                go_router config, auth-gated via redirect
    theme/                 color/spacing/typography tokens -> ThemeData
    widgets/               PrimaryButton, AppTextField, Loading/Error/EmptyView
  features/<name>/
    domain/                abstract repository interfaces (no Flutter/Dio import)
    data/                  concrete repository + API client implementations
    presentation/          Riverpod controllers + screens
```

Only `auth/` has all three layers filled in — it's the concrete example
the other 9 features (dashboard, search_profiles, offers, deal_analysis,
repair_analysis, favorites, notifications, settings) follow in Task #12.

## Networking (Band 4: "automatic token refresh, retry policy, central
error handling")

One shared `Dio` instance (`core/network/dio_factory.dart`) with two
interceptors, in this order:

1. **`AuthInterceptor`** — attaches `Authorization: Bearer <token>` to
   every request except `/auth/login|register|refresh`. On a `401`, it
   silently refreshes once (via a separate interceptor-free `Dio` instance,
   to avoid re-entering itself) and retries the original request. A v1
   simplification: concurrent 401s during an in-flight refresh don't queue
   — see the class doc comment.
2. **`RetryInterceptor`** — retries connection-level failures (timeout,
   connection error) up to twice with linear backoff. Never retries actual
   HTTP error responses (4xx/5xx) — those aren't transient.

`ErrorMapper` turns any `DioException` into an `AppException`, preferring
the backend's own `{code, message, details, correlation_id}` body (Band
10's unified error model) when present, falling back to a generic
network/unknown error otherwise.

## State management (Band 4: Riverpod, immutable state)

Pinned to **Riverpod 2.x** (`flutter_riverpod: ^2.6.1`), not the newer 3.x
line — see the comment in `pubspec.yaml` for why (3.x rewrote core APIs
shortly before this was written, with no local analyzer available here to
verify against it). `AuthController extends StateNotifier<AsyncValue<bool>>`
is the pattern every future feature controller follows.

## Design system (Band 18)

`core/theme/`: `AppColors.seed` is a placeholder seed color driving
Material 3's `ColorScheme.fromSeed` — **Task #19 (Branding-Tokens)** picks
the real brand color; every other color in the app derives from that one
constant. `AppSpacing` is a fixed spacing scale (4/8/16/24/32/48).
`AppTypography.fontFamily` is `null` (platform default) until Task #19
chooses a brand typeface.

## Known gaps

- No Flutter SDK in the sandbox this was built in — see "Status" above.
- `flutter_secure_storage` needs platform-level setup before it works on a
  real device/emulator (Android `minSdkVersion` 18+; iOS Keychain
  entitlements are usually automatic). Not yet verified on either platform.
- The `AuthInterceptor`'s refresh flow doesn't queue concurrent 401s (see
  its doc comment) — a deliberate v1 simplification, not an oversight.
- No app icon or splash screen yet — natural Task #19 (Branding) follow-up
  once `flutter create` has generated the platform folders they'd live in.
