import 'package:deal_hunter_ai/core/widgets/brand_mark.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  Widget wrap(Widget child) => MaterialApp(home: Scaffold(body: child));

  testWidgets('renders the search icon and the percent badge', (tester) async {
    await tester.pumpWidget(wrap(const BrandMark()));

    expect(find.byIcon(Icons.search), findsOneWidget);
    expect(find.byIcon(Icons.percent), findsOneWidget);
  });

  testWidgets('lays out at the given size', (tester) async {
    await tester.pumpWidget(wrap(const BrandMark(size: 100)));

    final renderBox = tester.renderObject<RenderBox>(find.byType(BrandMark));
    expect(renderBox.size, const Size(100, 100));
  });

  testWidgets('defaults to size 72 when unspecified', (tester) async {
    await tester.pumpWidget(wrap(const BrandMark()));

    final renderBox = tester.renderObject<RenderBox>(find.byType(BrandMark));
    expect(renderBox.size, const Size(72, 72));
  });
}
