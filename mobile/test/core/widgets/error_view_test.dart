import 'package:deal_hunter_ai/core/widgets/error_view.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  Widget wrap(Widget child) => MaterialApp(home: Scaffold(body: child));

  testWidgets('shows the message and no retry button when onRetry is omitted', (tester) async {
    await tester.pumpWidget(wrap(const ErrorView(message: 'Etwas ist schiefgelaufen.')));

    expect(find.text('Etwas ist schiefgelaufen.'), findsOneWidget);
    expect(find.byType(OutlinedButton), findsNothing);
  });

  testWidgets('shows a retry button that calls onRetry when tapped', (tester) async {
    var retried = false;
    await tester.pumpWidget(
      wrap(ErrorView(message: 'Netzwerkfehler.', onRetry: () => retried = true)),
    );

    expect(find.text('Erneut versuchen'), findsOneWidget);

    await tester.tap(find.byType(OutlinedButton));
    await tester.pump();

    expect(retried, isTrue);
  });
}
