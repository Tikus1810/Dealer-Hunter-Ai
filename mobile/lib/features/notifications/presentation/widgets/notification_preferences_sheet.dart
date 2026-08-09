import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/widgets/loading_view.dart';
import '../../domain/notification_preference.dart';
import '../notifications_providers.dart';

/// Backed by `GET`/`PUT /api/v1/notifications/preferences`. One switch per
/// (event, channel) pair (Band 11: opt-out model — a pair not yet in the
/// backend's response is implicitly enabled).
Future<void> showNotificationPreferencesSheet(BuildContext context) {
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    builder: (context) => const _NotificationPreferencesSheet(),
  );
}

class _NotificationPreferencesSheet extends ConsumerWidget {
  const _NotificationPreferencesSheet();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final preferencesAsync = ref.watch(notificationPreferencesControllerProvider);
    final controller = ref.read(notificationPreferencesControllerProvider.notifier);

    return Padding(
      padding: EdgeInsets.only(
        left: AppSpacing.lg,
        right: AppSpacing.lg,
        top: AppSpacing.lg,
        bottom: MediaQuery.of(context).viewInsets.bottom + AppSpacing.lg,
      ),
      child: preferencesAsync.when(
        data: (_) => SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text('Benachrichtigungseinstellungen', style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: AppSpacing.md),
              for (final event in NotificationEvents.all) ...[
                Text(NotificationEvents.label(event), style: Theme.of(context).textTheme.titleSmall),
                for (final channel in NotificationChannels.all)
                  SwitchListTile.adaptive(
                    contentPadding: EdgeInsets.zero,
                    title: Text(NotificationChannels.label(channel)),
                    // See search_profile_form_sheet.dart's identical
                    // override (including why it's `activeColor`, not the
                    // newer split `activeThumbColor`/`activeTrackColor`):
                    // the iOS-branch adaptive switch defaults to system
                    // green, not the app's brand yellow.
                    activeColor: AppColors.seed,
                    value: controller.isEnabled(event, channel),
                    onChanged: (value) => controller.setEnabled(event, channel, value),
                  ),
                const SizedBox(height: AppSpacing.sm),
              ],
            ],
          ),
        ),
        loading: () => const SizedBox(height: 200, child: LoadingView()),
        error: (error, stackTrace) => SizedBox(
          height: 120,
          child: Center(
            child: TextButton(
              onPressed: controller.refresh,
              child: const Text('Erneut versuchen'),
            ),
          ),
        ),
      ),
    );
  }
}
