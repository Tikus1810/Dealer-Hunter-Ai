import 'package:flutter/material.dart';

/// Typography tokens (Band 18: design system typography; Band 19:
/// Branding — the family/scale decision itself lands here).
class AppTypography {
  const AppTypography._();

  /// `null` — Material 3's platform default (Roboto on Android, San
  /// Francisco on iOS). Final decision (Band 19), not a deferred one:
  /// this app has no licensed custom typeface, and every custom-font
  /// route available without one adds a real, unverifiable-in-this-
  /// sandbox risk — either a new pub dependency (`google_fonts`, which
  /// fetches font files over the network at runtime) or bundled font
  /// binaries this environment has no way to source or license-check.
  /// Platform-native type also reads as more trustworthy for a
  /// "is this deal legit" product, and costs nothing in load time/APK
  /// size. Revisit only alongside a real brand refresh with licensed
  /// font files in hand — not as a follow-up task by itself.
  static const String? fontFamily = null;

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
