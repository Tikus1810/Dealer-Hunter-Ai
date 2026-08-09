import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';

import '../theme/app_spacing.dart';

/// Standard empty/placeholder state (Band 18: reusable widgets). Used both
/// for genuine "nothing here yet" states and, in this foundation build, as
/// the stand-in body for every screen whose real UI lands in Task #12.
class EmptyView extends StatelessWidget {
  const EmptyView({super.key, required this.message, this.icon = CupertinoIcons.tray});

  final String message;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // A plain gray outline icon floating on an otherwise-empty page
            // reads as "unfinished", not "intentionally empty" — a soft
            // brand-tinted circle behind it gives every empty state (offer
            // list, favorites, search profiles, notifications — all reuse
            // this one widget) the same deliberate, on-brand look instead
            // of looking like a stand-in nobody got back to.
            Container(
              width: 88,
              height: 88,
              decoration: BoxDecoration(
                color: colorScheme.primaryContainer,
                shape: BoxShape.circle,
              ),
              child: Icon(icon, size: 40, color: colorScheme.onPrimaryContainer),
            ),
            const SizedBox(height: AppSpacing.lg),
            Text(
              message,
              textAlign: TextAlign.center,
              style: theme.textTheme.bodyLarge?.copyWith(color: colorScheme.onSurfaceVariant),
            ),
          ],
        ),
      ),
    );
  }
}
