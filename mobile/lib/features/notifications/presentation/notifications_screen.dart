import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/error/app_exception.dart';
import '../../../core/widgets/empty_view.dart';
import '../../../core/widgets/error_view.dart';
import '../../../core/widgets/loading_view.dart';
import '../domain/notification.dart';
import 'notifications_providers.dart';
import 'widgets/notification_preferences_sheet.dart';

/// Backed by `GET /api/v1/notifications` + `POST /{id}/read`.
class NotificationsScreen extends ConsumerWidget {
  const NotificationsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final notificationsAsync = ref.watch(notificationsControllerProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Benachrichtigungen'),
        actions: [
          IconButton(
            icon: const Icon(Icons.tune),
            tooltip: 'Einstellungen',
            onPressed: () => showNotificationPreferencesSheet(context),
          ),
        ],
      ),
      body: notificationsAsync.when(
        data: (notifications) {
          if (notifications.isEmpty) {
            return const EmptyView(
              icon: Icons.notifications_outlined,
              message: 'Noch keine Benachrichtigungen.',
            );
          }
          return RefreshIndicator(
            onRefresh: () => ref.read(notificationsControllerProvider.notifier).refresh(),
            child: ListView.builder(
              itemCount: notifications.length,
              itemBuilder: (context, index) => _NotificationTile(notification: notifications[index]),
            ),
          );
        },
        loading: () => const LoadingView(),
        error: (error, stackTrace) => ErrorView(
          message: _errorMessage(error),
          onRetry: () => ref.read(notificationsControllerProvider.notifier).refresh(),
        ),
      ),
    );
  }

  String _errorMessage(Object error) {
    if (error is AppException) return error.message;
    return 'Ein unerwarteter Fehler ist aufgetreten.';
  }
}

class _NotificationTile extends ConsumerWidget {
  const _NotificationTile({required this.notification});

  final AppNotification notification;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return ListTile(
      leading: Icon(
        notification.isRead ? Icons.mail_outline : Icons.mark_email_unread,
        color: notification.isRead ? null : Theme.of(context).colorScheme.primary,
      ),
      title: Text(
        notification.title,
        style: TextStyle(
          fontWeight: notification.isRead ? FontWeight.normal : FontWeight.bold,
        ),
      ),
      subtitle: Text(notification.body),
      trailing: notification.isRead
          ? null
          : IconButton(
              icon: const Icon(Icons.check),
              tooltip: 'Als gelesen markieren',
              onPressed: () =>
                  ref.read(notificationsControllerProvider.notifier).markRead(notification.id),
            ),
      onTap: notification.isRead
          ? null
          : () => ref.read(notificationsControllerProvider.notifier).markRead(notification.id),
    );
  }
}
