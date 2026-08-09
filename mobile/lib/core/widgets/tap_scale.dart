import 'package:flutter/widgets.dart';

/// iOS-style tap feedback: a brief opacity/scale dip on press, no ripple.
/// Also adds a pointer cursor + a faint hover dim on non-touch input (a
/// mouse) — the exe/desktop-web-window build has a mouse and no ripple to
/// tell you something's interactive, so without this every tappable row
/// looked inert until actually clicked, which is exactly the kind of
/// small thing that makes a UI feel like a phone layout with a mouse
/// pointed at it rather than an actual desktop program.
///
/// `AppTheme` turns off Material's ripple/splash app-wide (the single
/// biggest "this is an Android app" tell), which means anything still
/// wrapped in a plain `InkWell`/`GestureDetector` gives *zero* visual
/// feedback on tap — worse than the Material default, not just
/// differently-styled. This is the replacement: the same dim-on-press
/// language `CupertinoButton` uses internally, as a reusable wrapper so
/// existing tappable rows/cards don't need a full Cupertino-widget
/// rewrite to feel responsive again.
class TapScale extends StatefulWidget {
  const TapScale({super.key, required this.onTap, required this.child, this.borderRadius});

  final VoidCallback onTap;
  final Widget child;
  final BorderRadius? borderRadius;

  @override
  State<TapScale> createState() => _TapScaleState();
}

class _TapScaleState extends State<TapScale> {
  bool _pressed = false;
  bool _hovered = false;

  void _setPressed(bool value) {
    if (_pressed != value) setState(() => _pressed = value);
  }

  @override
  Widget build(BuildContext context) {
    // Pressed wins over hover (0.55 vs 0.88) so a click still reads as a
    // click, not just a slightly-darker hover.
    final opacity = _pressed ? 0.55 : (_hovered ? 0.88 : 1.0);

    return MouseRegion(
      cursor: SystemMouseCursors.click,
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTapDown: (_) => _setPressed(true),
        onTapUp: (_) => _setPressed(false),
        onTapCancel: () => _setPressed(false),
        onTap: widget.onTap,
        child: AnimatedOpacity(
          opacity: opacity,
          duration: const Duration(milliseconds: 120),
          curve: Curves.easeOut,
          child: widget.child,
        ),
      ),
    );
  }
}
