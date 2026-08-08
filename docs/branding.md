# Branding (Band 19)

Band 19's spec (`Band 19/Band_19_Branding.md`) is a section-header
skeleton, not a filled specification (true of Bands 11–15 and 17–20 — see
the root [README.md](../README.md#status)) — everything below follows
standard practice for a small product's first brand pass, not a
documented Deal Hunter AI–specific requirement. It fills in the
skeleton's own "Required Sections" list.

## Vision

A visual identity that reads as **trustworthy** and **value-focused**
first — this app's whole premise is "is this second-hand device actually
a good deal, and can I trust the score/analysis that says so" — before
it reads as flashy. German/DACH market (see
[docs/analytics.md](analytics.md), the app's German-only notification
copy) informs tone: direct, factual, no hype language.

## Objectives

- One brand seed color driving the entire Material 3 `ColorScheme`
  (light + dark), so a future re-brand is a one-constant change.
- A small semantic-color vocabulary for the one recurring domain need
  raw Material colors don't cover: "this factor/score is good" vs.
  "this needs a second look" (DealBrain/RepairBrain result screens).
- A typography decision that is actually a *decision* — not a
  placeholder `null` waiting for someone to pick a font later.
- An app-icon concept that exists as a real, reviewable asset today, with
  a documented (not hand-waved) path to becoming real platform icon
  files once a Flutter SDK can scaffold `android/`/`ios/`.
- No regressions of Band 18's own design-system rule: no raw color
  literal outside `mobile/lib/core/theme/` except a widget with a
  genuinely one-off need.

## Architecture Impact

No new architectural surface — this Band operates entirely inside the
existing design-system token files from Band 18
(`mobile/lib/core/theme/`) plus one new small, reusable widget:

- `mobile/lib/core/theme/app_colors.dart` — brand seed (unchanged value,
  now documented as final) + new `positive(Brightness)` /
  `warning(Brightness)` semantic accessors.
- `mobile/lib/core/theme/app_typography.dart` — `fontFamily` decision
  documented as final (`null`, i.e. platform-native), plus a new
  `apply(TextTheme)` that layers weight/letter-spacing overrides onto
  Material 3's default type scale.
- `mobile/lib/core/theme/app_theme.dart` — now calls
  `AppTypography.apply(...)` when building `textTheme`.
- `mobile/lib/core/widgets/brand_mark.dart` — new, reusable in-app logo
  badge (pure Flutter widgets, no new asset-rendering dependency), used
  on the login/register screens.
- `mobile/assets/branding/app_icon.svg` — new, the app-icon master
  vector (not wired into the app or any platform target yet — see
  "Future Extension Points").

## Functional Requirements

- **Color**: `AppColors.seed` (`#2D6A4F`, deep muted green) drives
  `ColorScheme.fromSeed` for both light and dark themes, unchanged since
  it was already a deliberate Task #11 choice — this Band's job was to
  confirm and document it, not necessarily replace it. New semantic
  tokens `AppColors.positive(brightness)` / `AppColors.warning(brightness)`
  give explicit light/dark color pairs for "good" vs. "needs attention"
  domain states, replacing two raw `Colors.green`/`Colors.orange` literals
  that had drifted into `deal_analysis_screen.dart` in violation of Band
  18's own rule.
- **Typography**: platform-native font family (`fontFamily: null`),
  final decision — see the code comment in `app_typography.dart` for the
  reasoning (no licensed custom typeface exists; every alternative adds
  an unverifiable-in-this-sandbox risk). A small custom type-scale layer
  (`AppTypography.apply`) gives the app's own rhythm within that
  constraint: bolder titles, tighter letter-spacing on the large numeral
  role used for deal scores.
- **App icon**: `assets/branding/app_icon.svg` — a magnifying glass (the
  "hunt") resolving onto a price tag (the "deal"), in the app's own
  brand + semantic-positive colors. A simplified, dependency-free
  in-app rendition (`BrandMark` widget) is wired into the login and
  register screens now.

## Non-Functional Requirements

- **Performance**: no new pub dependencies, no network calls, no font
  binaries bundled — the app-icon asset is an inert SVG file the app
  itself never loads at runtime.
- **Security**: none of this touches user data or network I/O.
- **Maintainability**: exactly two files (`app_colors.dart`,
  `app_typography.dart`) own every brand decision; every consuming
  widget goes through them, never a literal.
- **Testability**: `AppColors.positive`/`warning` and
  `AppTypography.apply` are pure functions — covered by
  `mobile/test/core/theme/app_colors_test.dart` and
  `app_typography_test.dart` without needing a widget pump.
- **Accessibility**: `positive`/`warning` use explicit light/dark color
  pairs specifically because a single mid-tone color that passes WCAG
  contrast on a light surface can fail on a dark one, and vice versa —
  not verified against an automated contrast checker in this sandbox
  (none available), but chosen from Material's own tonal-palette shades
  (700/800 for light surfaces, 200/300-equivalent for dark), which are
  designed for exactly this.

## Standards

- Material 3 (`useMaterial3: true`, already established since Band 18/
  Task #11) — this Band works within that system, doesn't replace it.
- Band 18's design-system rule (tokens in `theme/`, no stray literals)
  is treated as binding, not aspirational — the two-literal drift found
  in `deal_analysis_screen.dart` while implementing this Band was fixed
  as part of it, not left for a separate task.

## Risks

- **No real Flutter SDK in this sandbox** (documented throughout Tasks
  #11/#12/CLAUDE.md): none of `AppTypography.apply`'s `TextTheme.copyWith`
  usage, `BrandMark`'s `Stack`/`Positioned` layout, or the new tests have
  run through a real `flutter test`/`analyze` yet. Verify against CI
  (`.github/workflows/ci.yml`'s `flutter` job) before trusting further,
  same caveat as every other Flutter-touching task.
- **No design-review stakeholder**: color/typography/icon choices here
  are a single considered pass, not validated against user testing or a
  hired designer — flagged, not hidden.
- **App icon is not yet a real platform icon**: no `android/`/`ios/`
  folders exist (`flutter create .` needs a real SDK), so
  `app_icon.svg` cannot yet be wired through `flutter_launcher_icons`.
  See "Future Extension Points".

## Acceptance Criteria

- [x] `AppColors.seed` documented as a final decision with rationale,
      not left as an unexplained placeholder.
- [x] Semantic status colors exist, are brightness-aware, and are used
      by every screen that previously hardcoded `Colors.green`/
      `Colors.orange` for the same purpose (verified via
      `grep -rn "Colors\.(red|green|orange|amber|blue|grey|gray|yellow)"
      mobile/lib` — zero matches outside `app_colors.dart`'s own
      explanatory comment).
- [x] `AppTypography.fontFamily` documented as a final decision, not a
      deferred one.
- [x] A reviewable app-icon asset exists (`app_icon.svg`) with a
      documented path to becoming real platform icons.
- [x] New pure-function logic (`AppColors.positive/warning`,
      `AppTypography.apply`) has unit test coverage.
- [ ] Verified against a real `flutter analyze`/`flutter test` run — not
      yet possible in this sandbox; carried forward as an open item,
      same as the rest of `mobile/`.

## Definition of Done

Code merged, `docs/branding.md` (this file) written, README links to it,
CLAUDE.md's existing "no color literal outside theme/" rule now has zero
known violations. Full closure (checking the last acceptance-criteria
box) is blocked on the same "no real Flutter SDK in this sandbox"
constraint documented since Task #11 — not on anything specific to this
Band.

## Future Extension Points

- **Real platform app icons**: once `flutter create .` has scaffolded
  `android/`/`ios/` against a real Flutter SDK, rasterize
  `app_icon.svg` to a 1024×1024 PNG and run it through
  `flutter_launcher_icons` (see the SVG file's own header comment for
  the exact steps) — do not hand-place icon files per platform/density.
- **Splash screen**: no `flutter_native_splash`-equivalent exists yet;
  `BrandMark` is ready to double as one once platform folders exist.
- **Custom typeface**: if a licensed brand font is ever acquired, it
  replaces `AppTypography.fontFamily`'s `null` in one place; no other
  file should need to change, by design.
- **Dark-mode contrast audit**: run `AppColors.positive`/`warning`
  against an automated WCAG contrast checker once one is available in
  the build environment (there is none in this sandbox) instead of
  relying on Material's own tonal-shade design intent.

## Review checklist

- [x] No new pub dependency added for a small, avoidable need
      (`flutter_svg` deliberately not added — see `brand_mark.dart`'s
      header comment).
- [x] Every color/typography decision has a one-paragraph "why", not
      just a value.
- [x] `ruff`/ CLAUDE.md conventions N/A here (Dart-only change); Dart
      side follows `mobile/analysis_options.yaml` (`prefer_const_
      constructors`, `require_trailing_commas`, etc.) as far as this
      sandbox can verify without a real analyzer.

## Traceability to Band 01

Band 1 (Master PRD) frames this product around **trust** (a stranger's
used device, a stranger's price) — Deal Score, Repair Report and Vision AI
all exist to make that trust legible. This Band's color/typography
choices (calm, factual, no hype) and the app-icon concept (a magnifying
glass finding a genuine deal, not a shouting sale badge) are a direct,
if informal, continuation of that same premise into the visual layer.
