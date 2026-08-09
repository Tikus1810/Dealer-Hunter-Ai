import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';

import '../theme/app_spacing.dart';

/// Standard error state (Band 18: reusable widgets; Band 04: "Central
/// error handling") — pair with `ErrorMapper`'s `AppException.message` so
/// every failed screen looks and behaves the same way.
class ErrorView extends StatelessWidget {
  const ErrorView({super.key, required this.message, this.onRetry});

  final String message;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              CupertinoIcons.exclamationmark_triangle,
              size: 44,
              color: Theme.of(context).colorScheme.error,
            ),
            const SizedBox(height: AppSpacing.md),
            Text(message, textAlign: TextAlign.center),
            if (onRetry != null) ...[
              const SizedBox(height: AppSpacing.md),
              OutlinedButton(onPressed: onRetry, child: const Text('Erneut versuchen')),
            ],
          ],
        ),
      ),
    );
  }
}
