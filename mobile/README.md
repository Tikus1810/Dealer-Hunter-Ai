# Deal Hunter AI — Flutter App

Flutter client for [Deal Hunter AI](../README.md), implementing
[Band 4](../Band%204/Band_04_Flutter.md) (Flutter Application) and
[Band 18](../Band%2018/Band_18_UI_UX_Design_System.md) (UI/UX Design
System — a template band, see the root README's "Known gaps").

## Status: foundation + core screens (Tasks #11-#12)

Every Band 4 "Core Feature" now has real UI wired end-to-end against the
real backend API, not just a reachable placeholder:

- **Offers** — category-filtered, paginated list (`OfferListScreen`) and
  detail view (`OfferDetailScreen`) with a favorite toggle and links into
  Deal/Repair Analysis.
- **Deal Analysis** — DealBrain score, confidence, market value/total cost,
  and the full explanation-factor breakdown (`DealAnalysisScreen`).
- **Repair Analysis** — an on-demand form (known defects in, RepairBrain
  report out: cost, time, difficulty, parts, risk notes)
  (`RepairAnalysisScreen`).
- **Favorites** — list (each row's offer fetched individually — see the
  screen's doc comment for why) with optimistic add/remove
  (`FavoritesController`).
- **Search Profiles** — full CRUD: list, create/edit bottom sheet, delete
  with confirmation (`SearchProfilesScreen`).
- **Notifications** — inbox with mark-as-read, plus a preferences bottom
  sheet (one switch per event×channel, opt-out model)
  (`NotificationsScreen`).
- **Settings** — notification preferences entry point + logout.
- **Dashboard** — navigation hub (built in Task #11, still the "Dashboard"
  screen; deeper dashboard *content* like a recent-deals feed was judged
  out of scope for this pass and left as a natural follow-up).

Only Authentication (Task #11) and everything above (Task #12) has real
UI; there is no remaining placeholder screen from the original Band 4
feature list.

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

Every feature now follows this layering (`auth/` was the Task #11
prototype; the rest landed in Task #12). No hand-written DTO uses code
generation (no `json_serializable`/`freezed`) — every domain entity has a
plain `fromJson` factory, matching the backend's own "explicit over
magic" style and keeping this buildable without `build_runner`.

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

- No Flutter SDK in the sandbox this was built in — see "Status" above;
  this now applies to significantly more code than at the end of Task #11
  (82 files / ~4200 lines total), so there's more surface area a real
  `flutter analyze`/`test` run could still turn up something in.
- `flutter_secure_storage` needs platform-level setup before it works on a
  real device/emulator (Android `minSdkVersion` 18+; iOS Keychain
  entitlements are usually automatic). Not yet verified on either platform.
- The `AuthInterceptor`'s refresh flow doesn't queue concurrent 401s (see
  its doc comment) — a deliberate v1 simplification, not an oversight.
- No app icon or splash screen yet — natural Task #19 (Branding) follow-up
  once `flutter create` has generated the platform folders they'd live in.
- The offer detail screen's "Original-Angebot anzeigen" button shows the
  source URL in a dialog rather than opening it — no `url_launcher`
  dependency was added to keep this task's package-verification surface
  smaller; trivial to wire in later.
- Favorites and the notification inbox fetch all pages up front rather
  than paginating in the UI (`FavoritesRepository.listAllFavorites`,
  `NotificationsRepository.listAllNotifications`) — reasonable at the list
  sizes those features realistically have today; revisit if that changes.
- No widget tests (`testWidgets`) — only pure-Dart unit tests against fake
  repositories (`ErrorMapper`, `AuthController`, `FavoritesController`,
  `NotificationPreferencesController`). Widget/golden tests are more
  naturally Task #13's ("Test-Framework & CI Quality Gates") territory.
