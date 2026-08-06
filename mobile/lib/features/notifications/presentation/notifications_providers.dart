import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/di/providers.dart';
import '../data/notifications_api.dart';
import '../data/notifications_repository_impl.dart';
import '../domain/notification.dart';
import '../domain/notification_preference.dart';
import '../domain/notifications_repository.dart';
import 'notification_preferences_controller.dart';
import 'notifications_controller.dart';

final notificationsApiProvider = Provider<NotificationsApi>(
  (ref) => NotificationsApi(ref.watch(dioProvider)),
);

final notificationsRepositoryProvider = Provider<NotificationsRepository>((ref) {
  return NotificationsRepositoryImpl(
    api: ref.watch(notificationsApiProvider),
    errorMapper: ref.watch(errorMapperProvider),
  );
});

final notificationsControllerProvider =
    StateNotifierProvider<NotificationsController, AsyncValue<List<AppNotification>>>((ref) {
  return NotificationsController(ref.watch(notificationsRepositoryProvider));
});

final notificationPreferencesControllerProvider = StateNotifierProvider<
    NotificationPreferencesController, AsyncValue<List<NotificationPreference>>>((ref) {
  return NotificationPreferencesController(ref.watch(notificationsRepositoryProvider));
});
