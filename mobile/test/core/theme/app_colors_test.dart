import 'package:deal_hunter_ai/core/theme/app_colors.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('AppColors semantic status colors', () {
    test('positive() and warning() pick the dark-mode variant on a dark surface', () {
      expect(AppColors.positive(Brightness.dark), isNot(AppColors.positive(Brightness.light)));
      expect(AppColors.warning(Brightness.dark), isNot(AppColors.warning(Brightness.light)));
    });

    test('positive() and warning() are stable for the same brightness', () {
      expect(AppColors.positive(Brightness.light), AppColors.positive(Brightness.light));
      expect(AppColors.warning(Brightness.dark), AppColors.warning(Brightness.dark));
    });

    test('positive and warning never resolve to the same color for either brightness', () {
      // Band 18's own rule this token set exists to satisfy: a factor's
      // polarity (good vs. needs-attention) must stay visually
      // distinguishable — a color collision here would silently defeat
      // that for every screen that uses these tokens.
      expect(AppColors.positive(Brightness.light), isNot(AppColors.warning(Brightness.light)));
      expect(AppColors.positive(Brightness.dark), isNot(AppColors.warning(Brightness.dark)));
    });
  });
}
