import 'package:flutter/material.dart';

/// Color tokens (Band 18: design system color tokens; Band 19: Branding —
/// this file is where that Band's palette decision actually lands).
class AppColors {
  const AppColors._();

  /// Brand seed for Material 3's `ColorScheme.fromSeed` — every other role
  /// in the app's `ColorScheme` (primary/secondary/tertiary/surface/...)
  /// derives from this one constant, light and dark alike.
  ///
  /// **Third design pass ("Onyx + Candy Blue")**: replaces the second
  /// pass's gold/yellow (still documented below for history, same as that
  /// pass documented the original green it replaced) — same explicit,
  /// deliberate-pivot pattern, not a silent overwrite. Apple's own
  /// `systemBlue` (dark mode, `#0A84FF`) rather than a custom "candy"
  /// blue: it's already tuned for legibility as body text on a near-black
  /// surface, which a more saturated/lighter blue usually isn't.
  ///
  /// Previous (second pass): a bold gold/yellow, close to Apple's own
  /// `systemYellow` (`#FFD60A`/`#FFCC00` across iOS versions), chosen when
  /// the direction was "less Material/Android-coded, more iOS-coded" for
  /// the whole app. `docs/branding.md` still records the original green
  /// rationale from the very first pass.
  static const seed = Color(0xFF0A84FF);

  /// True black ("Onyx") — `AppTheme` now builds *both* its light and dark
  /// `ThemeData` around this fixed black-background/blue-accent look
  /// rather than a conventional light/dark pair (see that file). Broken
  /// out as its own named constant, not just used inline, so anything
  /// that needs to match the page background exactly (not a
  /// `colorScheme.surface` tint) has one source of truth. Left as pure
  /// black on purpose in the third pass — see `surfaceDark` below for
  /// where the "feels cold" feedback actually got addressed.
  static const backgroundBlack = Color(0xFF000000);

  /// Cards/sheets/nav-bar surface tone, one layer up from
  /// `backgroundBlack` (pure black-on-black has no depth cues at all).
  ///
  /// **Warmed in the third pass**: was iOS's own neutral `systemGray6`
  /// dark (`#1C1C1E`, R=G swapped with a cool blue-leaning B channel) —
  /// direct feedback was that the black/dark-gray combo read as "cold".
  /// This tone nudges the red channel above the blue channel (R32 vs B26,
  /// vs. the old tone's R28/B30 — blue *higher* than red) for a slightly
  /// warm, "onyx" undertone instead of a technical/cool one — subtle on
  /// purpose: enough to warm the large surface areas (cards, sheets)
  /// without the app's actual accent color (`seed`, now blue — a cool hue
  /// by nature) fighting it.
  static const surfaceDark = Color(0xFF201E1A);

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
