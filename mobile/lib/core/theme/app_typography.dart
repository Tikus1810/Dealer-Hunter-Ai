import 'package:flutter/material.dart';

/// Typography tokens (Band 18: design system typography; Band 19:
/// Branding — the family/scale decision itself lands here).
class AppTypography {
  const AppTypography._();

  /// "Space Grotesk" (Band 19: Branding, third design pass — explicit
  /// pivot from the `null`/platform-default decision below, kept for
  /// history).
  ///
  /// Bundled locally (`assets/fonts/space_grotesk/`, declared in
  /// `pubspec.yaml`), not fetched via the `google_fonts` pub package —
  /// same reasoning as `BrandMark`'s "no `flutter_svg` dependency" note:
  /// one small addition doesn't justify a new pub dependency with its own
  /// version-compatibility risk, and `google_fonts` fetches over the
  /// network at runtime by default, which a bundled asset avoids
  /// entirely (no first-launch font flash, works offline). OFL-licensed
  /// (Google Fonts' own distribution, `assets/fonts/space_grotesk/
  /// OFL.txt`), free to bundle and redistribute.
  ///
  /// **Previous decision (kept for history)**: `null` — Material 3's
  /// platform default (Roboto on Android, San Francisco on iOS). The
  /// original reasoning doesn't apply once the font is actually in hand
  /// (sourced from Google Fonts' own repo, license included) rather than
  /// hypothetical — the real remaining tradeoff is platform-native type
  /// reading as slightly more "trustworthy" for a deal-listing product,
  /// which was an explicit, deliberate one to accept for a distinctive
  /// brand look instead.
  static const String fontFamily = 'Space Grotesk';

  /// Weight/spacing overrides layered onto Material 3's default type
  /// scale, applied in [AppTheme]. Keeps the platform font but gives the
  /// app's own rhythm: tighter letter-spacing on large numerals (deal
  /// scores, prices — this app's actual hero content) and a slightly
  /// bolder title weight than Material's default, for legibility at a
  /// glance while scanning a list of offers.
  static const _titleWeight = FontWeight.w700;
  static const _numeralLetterSpacing = -0.5;

  static TextTheme apply(TextTheme base) {
    return base.copyWith(
      displayMedium: base.displayMedium?.copyWith(
        fontWeight: _titleWeight,
        letterSpacing: _numeralLetterSpacing,
      ),
      titleLarge: base.titleLarge?.copyWith(fontWeight: _titleWeight),
      titleMedium: base.titleMedium?.copyWith(fontWeight: _titleWeight),
    );
  }
}
