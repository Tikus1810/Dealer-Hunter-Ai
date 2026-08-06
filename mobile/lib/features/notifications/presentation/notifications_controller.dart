import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../domain/notification.dart';
import '../domain/notifications_repository.dart';

class NotificationsController extends StateNotifier<AsyncValue<List<AppNotification>>> {
  NotificationsController(this._repository) : super(const AsyncValue.loading()) {
    refresh();
  }

  final NotificationsRepository _repository;

  Future<void> refresh() async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(_repository.listAllNotifications);
  }

  /// Optimistically flips `isRead` locally, then confirms with the server —
  /// a failed request just gets silently corrected on the next `refresh()`
  /// rather than needing its own rollback (marking read is low-stakes).
  Future<void> markRead(String notificationId) async {
    final current = state.valueOrNull;
    if (current == null) return;

    state = AsyncValue.data([
      for (final notification in current)
        if (notification.id == notificationId)
          AppNotification(
            id: notification.id,
            event: notification.event,
            channel: notification.channel,
            title: notification.title,
            body: notification.body,
            isRead: true,
            createdAt: notification.createdAt,
          )
        else
          notification,
    ]);

    try {
      await _repository.markRead(notificationId);
    } catch (_) {
      // Not worth surfacing an error for — a stale unread badge corrects
      // itself on the next refresh.
    }
  }
}
