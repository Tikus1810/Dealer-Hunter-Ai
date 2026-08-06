import 'notification.dart';
import 'notification_preference.dart';

abstract class NotificationsRepository {
  /// Fetches every notification across all pages — the inbox screen shows
  /// them all at once, same simplification as `FavoritesRepository`.
  Future<List<AppNotification>> listAllNotifications();

  Future<void> markRead(String notificationId);

  Future<List<NotificationPreference>> getPreferences();

  Future<NotificationPreference> setPreference({
    required String event,
    required String channel,
    required bool enabled,
  });
}
