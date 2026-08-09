import 'package:deal_hunter_ai/core/widgets/brand_mark.dart';
import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  Widget wrap(Widget child) => MaterialApp(home: Scaffold(body: child));

  testWidgets('renders the wolf mark and the AI spark badge', (tester) async {
    await tester.pumpWidget(wrap(const BrandMark()));
    // SvgPicture loads its asset asynchronously even for a bundled asset
    // — one pump lets that first frame settle before asserting.
    await tester.pump();

    // The wolf is real vector artwork (see brand_mark.dart's docstring on
    // why an SVG asset now, not hand-drawn shapes), and the AI-spark
    // badge is a hand-drawn CustomPainter, not a second asset. Asserting
    // on widget *types* here, not the specific asset path/shape, so this
    // test survives another "swap the mark" pass like this file's own
    // history already had once.
    expect(find.byType(SvgPicture), findsOneWidget);
    expect(find.byType(CustomPaint), findsWidgets);
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
