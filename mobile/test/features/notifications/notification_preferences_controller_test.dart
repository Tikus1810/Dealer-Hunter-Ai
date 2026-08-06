import 'package:deal_hunter_ai/features/notifications/domain/notification.dart';
import 'package:deal_hunter_ai/features/notifications/domain/notification_preference.dart';
import 'package:deal_hunter_ai/features/notifications/domain/notifications_repository.dart';
import 'package:deal_hunter_ai/features/notifications/presentation/notification_preferences_controller.dart';
import 'package:flutter_test/flutter_test.dart';

class _FakeNotificationsRepository implements NotificationsRepository {
  _FakeNotificationsRepository({List<NotificationPreference>? initial})
      : _preferences = List.of(initial ?? const []);

  final List<NotificationPreference> _preferences;

  @override
  Future<List<AppNotification>> listAllNotifications() async => const [];

  @override
  Future<void> markRead(String notificationId) async {}

  @override
  Future<List<NotificationPreference>> getPreferences() async => List.of(_preferences);

  @override
  Future<NotificationPreference> setPreference({
    required String event,
    required String channel,
    required bool enabled,
  }) async {
    final updated = NotificationPreference(event: event, channel: channel, enabled: enabled);
    _preferences.removeWhere((p) => p.event == event && p.channel == channel);
    _preferences.add(updated);
    return updated;
  }
}

Future<void> _flushMicrotasks() => Future<void>.delayed(Duration.zero);

void main() {
  test('a pair absent from the backend defaults to enabled (opt-out model)', () async {
    final controller = NotificationPreferencesController(_FakeNotificationsRepository());
    await _flushMicrotasks();

    expect(controller.isEnabled('saved_search_match', 'push'), true);
  });

  test('an explicit disabled preference is respected', () async {
    final repository = _FakeNotificationsRepository(
      initial: const [
        NotificationPreference(event: 'saved_search_match', channel: 'push', enabled: false),
      ],
    );
    final controller = NotificationPreferencesController(repository);
    await _flushMicrotasks();

    expect(controller.isEnabled('saved_search_match', 'push'), false);
    expect(controller.isEnabled('saved_search_match', 'email'), true); // different channel
  });

  test('setEnabled updates local state without a full refresh', () async {
    final controller = NotificationPreferencesController(_FakeNotificationsRepository());
    await _flushMicrotasks();

    await controller.setEnabled('price_drop', 'push', false);

    expect(controller.isEnabled('price_drop', 'push'), false);
    expect(controller.isEnabled('price_drop', 'email'), true);
  });

  test('setEnabled replaces rather than duplicates an existing preference', () async {
    final repository = _FakeNotificationsRepository(
      initial: const [
        NotificationPreference(event: 'price_drop', channel: 'push', enabled: false),
      ],
    );
    final controller = NotificationPreferencesController(repository);
    await _flushMicrotasks();

    await controller.setEnabled('price_drop', 'push', true);

    expect(controller.isEnabled('price_drop', 'push'), true);
    expect(controller.state.valueOrNull?.length, 1);
  });
}
