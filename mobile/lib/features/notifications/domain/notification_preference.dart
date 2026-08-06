/// Mirrors the backend's `NotificationPreferenceResponse`.
class NotificationPreference {
  const NotificationPreference({
    required this.event,
    required this.channel,
    required this.enabled,
  });

  final String event;
  final String channel;
  final bool enabled;

  factory NotificationPreference.fromJson(Map<String, dynamic> json) {
    return NotificationPreference(
      event: json['event'] as String,
      channel: json['channel'] as String,
      enabled: json['enabled'] as bool,
    );
  }
}

/// The (event, channel) pairs the backend understands — mirrors
/// `NotificationEvent`/`NotificationChannel`
/// (`backend/app/modules/notifications/domain/entities.py`). The
/// preferences screen renders one row per combination; a combination
/// absent from the backend's response is implicitly enabled (Band 11:
/// opt-out model).
class NotificationEvents {
  const NotificationEvents._();

  static const savedSearchMatch = 'saved_search_match';
  static const priceDrop = 'price_drop';
  static const dealScoreReady = 'deal_score_ready';

  static const all = [savedSearchMatch, priceDrop, dealScoreReady];

  // Matched against string literals rather than the constants above to
  // stay unambiguously a constant pattern in Dart 3's switch-expression
  // syntax (a bare identifier there can be read as a new variable binding
  // instead of a value match, depending on how it resolves).
  static String label(String event) => switch (event) {
        'saved_search_match' => 'Treffer für gespeicherte Suche',
        'price_drop' => 'Preissenkung',
        'deal_score_ready' => 'Deal-Score verfügbar',
        _ => event,
      };
}

class NotificationChannels {
  const NotificationChannels._();

  static const push = 'push';
  static const email = 'email';

  static const all = [push, email];

  static String label(String channel) => switch (channel) {
        'push' => 'Push',
        'email' => 'E-Mail',
        _ => channel,
      };
}
