import 'package:flutter/material.dart';

import '../theme/app_colors.dart';

/// The in-app brand mark (Band 19: Branding) — a simplified, pure-Flutter
/// rendition of `assets/branding/app_icon.svg`'s "magnifying glass finds
/// a deal" motif, sized for use inside the app itself (auth screens,
/// splash) rather than as a platform app icon.
///
/// Deliberately drawn with `Icon`/`Container` instead of rendering the SVG
/// asset: adding SVG support means a new pub dependency (`flutter_svg`)
/// with its own version-compatibility risk against this project's pinned
/// Flutter/Dart SDK — a real, project-specific caution after go_router and
/// flutter_secure_storage both needed downgrades the first time a real
/// Flutter SDK ever resolved this app's dependencies (see CLAUDE.md). Not
/// worth taking on for one small in-app badge; revisit once the SVG asset
/// is actually needed for more than this.
class BrandMark extends StatelessWidget {
  const BrandMark({super.key, this.size = 72});

  final double size;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: AppColors.seed,
        borderRadius: BorderRadius.circular(size * 0.28),
      ),
      child: Stack(
        alignment: Alignment.center,
        children: [
          Icon(Icons.search, color: Colors.white, size: size * 0.55),
          Positioned(
            right: size * 0.14,
            bottom: size * 0.14,
            child: Container(
              width: size * 0.34,
              height: size * 0.34,
              decoration: BoxDecoration(
                // Fixed brand-mark badge — unlike in-content status colors
                // (AppColors.positive/warning), the logo itself doesn't
                // follow the surrounding theme's brightness, same as a
                // real app icon wouldn't.
                color: AppColors.positive(Brightness.light),
                shape: BoxShape.circle,
              ),
              child: Icon(Icons.percent, color: Colors.white, size: size * 0.2),
            ),
          ),
        ],
      ),
    );
  }
}
