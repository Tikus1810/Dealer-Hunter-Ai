import 'package:flutter/material.dart';

/// Color tokens (Band 18: design system color tokens).
///
/// `seed` is a neutral placeholder for Material 3's `ColorScheme.fromSeed`
/// — Task #19 (Branding) picks the real brand color; every other token in
/// this design system derives from it, so swapping this one constant is
/// meant to be the entire re-brand.
class AppColors {
  const AppColors._();

  static const seed = Color(0xFF2D6A4F);
}
