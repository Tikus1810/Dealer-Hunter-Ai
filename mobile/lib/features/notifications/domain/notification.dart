/// Mirrors the backend's `NotificationResponse`
/// (`backend/app/modules/notifications/presentation/schemas.py`).
class AppNotification {
  const AppNotification({
    required this.id,
    required this.event,
    required this.channel,
    required this.title,
    required this.body,
    required this.isRead,
    this.createdAt,
  });

  final String id;
  final String event;
  final String channel;
  final String title;
  final String body;
  final bool isRead;
  final DateTime? createdAt;

  factory AppNotification.fromJson(Map<String, dynamic> json) {
    final createdAtRaw = json['created_at'];
    return AppNotification(
      id: json['id'] as String,
      event: json['event'] as String,
      channel: json['channel'] as String,
      title: json['title'] as String,
      body: json['body'] as String,
      isRead: json['is_read'] as bool,
      createdAt: createdAtRaw is String ? DateTime.parse(createdAtRaw) : null,
    );
  }
}
