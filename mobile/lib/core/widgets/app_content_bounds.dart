import 'package:flutter/widgets.dart';

/// Caps a screen's scrollable content to a sane reading/list width and
/// centers it — without this, every list screen just stretches its
/// mobile-column layout edge-to-edge across whatever width the window
/// happens to be, which on a resized desktop window or the Windows exe
/// reads as "a phone layout that got wide", not an actual desktop
/// program's content column (compare: Mail, Slack, any real desktop
/// app's message/item list is a bounded column, not full-bleed).
///
/// [maxWidth] defaults to a list-row-friendly width; the dashboard uses a
/// wider one since its grid genuinely benefits from more horizontal
/// space (see `dashboard_screen.dart`).
class AppContentBounds extends StatelessWidget {
  const AppContentBounds({super.key, required this.child, this.maxWidth = 760});

  final Widget child;
  final double maxWidth;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: ConstrainedBox(constraints: BoxConstraints(maxWidth: maxWidth), child: child),
    );
  }
}
