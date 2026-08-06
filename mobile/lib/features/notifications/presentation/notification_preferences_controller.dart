import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../domain/notification_preference.dart';
import '../domain/notifications_repository.dart';

class NotificationPreferencesController
    extends StateNotifier<AsyncValue<List<NotificationPreference>>> {
  NotificationPreferencesController(this._repository) : super(const AsyncValue.loading()) {
    refresh();
  }

  final NotificationsRepository _repository;

  Future<void> refresh() async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(_repository.getPreferences);
  }

  /// `event`/`channel` from `NotificationEvents`/`NotificationChannels`
  /// (`domain/notification_preference.dart`).
  bool isEnabled(String event, String channel) {
    final preferences = state.valueOrNull;
    if (preferences == null) return true; // still loading => assume default (enabled)
    final match = preferences.where((p) => p.event == event && p.channel == channel);
    return match.isEmpty ? true : match.first.enabled; // Band 11: opt-out model
  }

  Future<void> setEnabled(String event, String channel, bool enabled) async {
    final updated = await _repository.setPreference(
      event: event,
      channel: channel,
      enabled: enabled,
    );
    final current = state.valueOrNull ?? const [];
    final next = current
        .where((preference) => !(preference.event == event && preference.channel == channel))
        .toList()
      ..add(updated);
    state = AsyncValue.data(next);
  }
}
