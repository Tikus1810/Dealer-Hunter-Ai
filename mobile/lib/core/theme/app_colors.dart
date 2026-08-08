import 'package:flutter/material.dart';

/// Color tokens (Band 18: design system color tokens; Band 19: Branding —
/// this file is where that Band's palette decision actually lands).
class AppColors {
  const AppColors._();

  /// Brand seed for Material 3's `ColorScheme.fromSeed` — every other role
  /// in the app's `ColorScheme` (primary/secondary/tertiary/surface/...)
  /// derives from this one constant, light and dark alike.
  ///
  /// Final brand color (Band 19), not a placeholder: a deep, muted green.
  /// "Deal Hunter" is fundamentally about *value found* — money saved,
  /// devices rescued from landfill instead of bought new — and green reads
  /// as "savings"/"go" across DACH audiences (this product's actual
  /// market, see `docs/analytics.md`) without the over-used, fintech-coded
  /// brightness of a pure `#00C853`-style green. Kept deliberately close to
  /// its Task #11 draft value (`0xFF2D6A4F`) — that value was already a
  /// considered choice, not a random placeholder; Band 19's job was to
  /// confirm and document it as final, not necessarily replace it.
  static const seed = Color(0xFF2D6A4F);

  // Semantic status colors — domain meaning (deal-score polarity: a
  // factor/score is *good* or *needs attention*), not brand identity, so
  // they're separate from the `seed`-derived ColorScheme roles above. Used
  // by DealBrain/RepairBrain result screens (e.g.
  // features/deal_analysis/presentation/deal_analysis_screen.dart) instead
  // of raw `Colors.green`/`Colors.orange` literals, which is what these
  // replaced — Band 18's own rule ("no color literal outside theme/") had
  // drifted in exactly those two call sites before this pass.
  //
  // Explicit light/dark pairs, not one literal + opacity: WCAG AA contrast
  // against each surface color needs checking per-brightness, and a single
  // mid-tone green/orange that passes on a white surface can fail on a
  // near-black one (and vice versa).
  static const _positiveLight = Color(0xFF2E7D32);
  static const _positiveDark = Color(0xFF81C784);
  static const _warningLight = Color(0xFFE65100);
  static const _warningDark = Color(0xFFFFB74D);

  /// "This is good" — e.g. a deal-score explanation factor pulling the
  /// score up, or a score in the "good deal" band.
  static Color positive(Brightness brightness) =>
      brightness == Brightness.dark ? _positiveDark : _positiveLight;

  /// "This needs a second look" — the middle band between `positive` and
  /// the theme's own `ColorScheme.error` (reserved for the worst band /
  /// actual errors, not reused here so the two stay visually distinct).
  static Color warning(Brightness brightness) =>
      brightness == Brightness.dark ? _warningDark : _warningLight;
}
