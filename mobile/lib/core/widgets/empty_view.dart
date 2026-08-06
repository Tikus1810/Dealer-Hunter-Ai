import 'package:flutter/material.dart';

import '../theme/app_spacing.dart';

/// Standard empty/placeholder state (Band 18: reusable widgets). Used both
/// for genuine "nothing here yet" states and, in this foundation build, as
/// the stand-in body for every screen whose real UI lands in Task #12.
class EmptyView extends StatelessWidget {
  const EmptyView({super.key, required this.message, this.icon = Icons.inbox_outlined});

  final String message;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 48, color: Theme.of(context).colorScheme.outline),
            const SizedBox(height: AppSpacing.md),
            Text(message, textAlign: TextAlign.center),
          ],
        ),
      ),
    );
  }
}
