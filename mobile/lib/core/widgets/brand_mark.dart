import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../theme/app_colors.dart';

/// The in-app brand mark (Band 19: Branding, third design pass) — a
/// glassy blue squircle with a black howling-wolf mark, plus a small "AI
/// spark" badge to make the app's actual differentiator (this isn't just
/// deal *listing*, it's AI-scored deal *hunting*) visible in the mark
/// itself, not just spelled out in the app name. Used inside the app
/// itself (auth screens, dashboard header) rather than as a platform app
/// icon.
///
/// **Fourth redesign within the same pass**: went mark → mark-plus-spark-
/// badge (this file) → tried swapping the mark itself for a bullseye
/// (kept the spark badge) → reverted the mark back to the wolf on
/// explicit "looks better" feedback, spark badge kept throughout. The
/// wolf-vs-bullseye choice is purely a visual call, not an architectural
/// one — both are a single `SvgPicture.asset` behind the same badge, so
/// swapping the mark again later is a one-file, one-asset change.
///
/// The spark badge is drawn with a `CustomPainter` rather than a second
/// image asset — a 4-point "twinkle" is simple enough geometry (four
/// concave bezier curves from a center point) that hand-drawing it is
/// more reliable than sourcing a second icon whose exact silhouette
/// isn't visually confirmed ahead of time, and it's the same glyph
/// language other products use as AI shorthand (Gemini, Copilot, Apple
/// Intelligence) — recognizable rather than a novel invented icon.
///
/// `assets/branding/wolf_howl.svg`: "Wolf head" by Lorc (game-icons.net /
/// github.com/game-icons/icons), CC BY 3.0 — recolored solid black and
/// stripped of its original black background square (this widget
/// supplies its own gradient background instead). Full attribution in
/// `assets/branding/CREDITS.md`.
class BrandMark extends StatelessWidget {
  const BrandMark({super.key, this.size = 72});

  final double size;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        children: [
          Container(
            width: size,
            height: size,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(size * 0.28),
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [Color.lerp(AppColors.seed, Colors.white, 0.22)!, AppColors.seed],
              ),
              boxShadow: [
                BoxShadow(
                  color: AppColors.seed.withValues(alpha: 0.55),
                  blurRadius: size * 0.22,
                  spreadRadius: -size * 0.04,
                  offset: Offset(0, size * 0.06),
                ),
              ],
            ),
            padding: EdgeInsets.all(size * 0.2),
            child: SvgPicture.asset('assets/branding/wolf_howl.svg'),
          ),
          // The "AI spark" badge — same corner/proportions the very
          // first version of this mark used for its percent badge, a
          // deliberate callback so the badge reads as "an accent on the
          // mark", not a randomly placed sticker.
          Positioned(
            right: size * 0.08,
            bottom: size * 0.08,
            child: Container(
              width: size * 0.36,
              height: size * 0.36,
              decoration: const BoxDecoration(color: Colors.white, shape: BoxShape.circle),
              padding: EdgeInsets.all(size * 0.09),
              child: const CustomPaint(painter: _SparkPainter(color: AppColors.seed)),
            ),
          ),
        ],
      ),
    );
  }
}

/// Draws a 4-point "twinkle" spark — the common AI-feature glyph — as
/// four concave bezier curves meeting at N/E/S/W points, rather than a
/// straight-edged diamond/star (a straight-edged shape reads as a
/// generic star, not the "AI" spark specifically).
class _SparkPainter extends CustomPainter {
  const _SparkPainter({required this.color});

  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final cx = size.width / 2;
    final cy = size.height / 2;
    final r = size.shortestSide / 2;
    final pull = r * 0.16;

    final path = Path()
      ..moveTo(cx, cy - r)
      ..quadraticBezierTo(cx + pull, cy - pull, cx + r, cy)
      ..quadraticBezierTo(cx + pull, cy + pull, cx, cy + r)
      ..quadraticBezierTo(cx - pull, cy + pull, cx - r, cy)
      ..quadraticBezierTo(cx - pull, cy - pull, cx, cy - r)
      ..close();

    canvas.drawPath(path, Paint()..color = color);
  }

  @override
  bool shouldRepaint(covariant _SparkPainter oldDelegate) => oldDelegate.color != color;
}
