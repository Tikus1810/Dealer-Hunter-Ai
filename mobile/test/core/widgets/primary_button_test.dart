import 'package:deal_hunter_ai/core/widgets/primary_button.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  Widget wrap(Widget child) => MaterialApp(home: Scaffold(body: child));

  testWidgets('shows the label and calls onPressed when tapped', (tester) async {
    var tapped = false;
    await tester.pumpWidget(
      wrap(PrimaryButton(label: 'Anmelden', onPressed: () => tapped = true)),
    );

    expect(find.text('Anmelden'), findsOneWidget);

    await tester.tap(find.byType(PrimaryButton));
    await tester.pump();

    expect(tapped, isTrue);
  });

  testWidgets('shows a spinner instead of the label while loading', (tester) async {
    await tester.pumpWidget(
      wrap(PrimaryButton(label: 'Anmelden', isLoading: true, onPressed: () {})),
    );

    expect(find.text('Anmelden'), findsNothing);
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
  });

  testWidgets('disables the button while loading, even with an onPressed set', (tester) async {
    var tapped = false;
    await tester.pumpWidget(
      wrap(PrimaryButton(label: 'Anmelden', isLoading: true, onPressed: () => tapped = true)),
    );

    final button = tester.widget<ElevatedButton>(find.byType(ElevatedButton));
    expect(button.onPressed, isNull);

    await tester.tap(find.byType(PrimaryButton), warnIfMissed: false);
    await tester.pump();
    expect(tapped, isFalse);
  });

  testWidgets('disables the button when onPressed is null', (tester) async {
    await tester.pumpWidget(wrap(const PrimaryButton(label: 'Anmelden', onPressed: null)));

    final button = tester.widget<ElevatedButton>(find.byType(ElevatedButton));
    expect(button.onPressed, isNull);
  });
}
