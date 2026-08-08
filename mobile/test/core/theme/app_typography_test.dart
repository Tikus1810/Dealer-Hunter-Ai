import 'package:deal_hunter_ai/core/theme/app_typography.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('AppTypography.apply', () {
    test('boosts title weight without dropping other TextTheme roles', () {
      const base = TextTheme(
        bodyMedium: TextStyle(fontSize: 14),
        titleLarge: TextStyle(fontSize: 22, fontWeight: FontWeight.w400),
      );

      final themed = AppTypography.apply(base);

      expect(themed.bodyMedium?.fontSize, 14, reason: 'unrelated roles must pass through untouched');
      expect(themed.titleLarge?.fontWeight, FontWeight.w700);
      expect(themed.titleLarge?.fontSize, 22, reason: 'size is inherited, only weight is overridden');
    });

    test('tightens letter-spacing on displayMedium (the deal-score numeral role)', () {
      const base = TextTheme(displayMedium: TextStyle(fontSize: 45));

      final themed = AppTypography.apply(base);

      expect(themed.displayMedium?.letterSpacing, lessThan(0));
    });

    test('is a no-op for a role that was null on the base theme', () {
      const base = TextTheme();

      final themed = AppTypography.apply(base);

      expect(themed.labelSmall, isNull);
    });
  });
}
