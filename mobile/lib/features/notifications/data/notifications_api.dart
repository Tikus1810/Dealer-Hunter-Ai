import 'package:dio/dio.dart';

/// Thin wrapper over `/api/v1/notifications*`
/// (`backend/app/modules/notifications/presentation/router.py`).
class NotificationsApi {
  const NotificationsApi(this._dio);

  final Dio _dio;

  Future<Map<String, dynamic>> listNotifications({required int page, required int pageSize}) async {
    final response = await _dio.get<Map<String, dynamic>>(
      '/notifications',
      queryParameters: {'page': page, 'page_size': pageSize},
    );
    return response.data ?? const <String, dynamic>{};
  }

  Future<void> markRead(String notificationId) async {
    await _dio.post<void>('/notifications/$notificationId/read');
  }

  Future<List<dynamic>> getPreferences() async {
    final response = await _dio.get<List<dynamic>>('/notifications/preferences');
    return response.data ?? const [];
  }

  Future<Map<String, dynamic>> setPreference({
    required String event,
    required String channel,
    required bool enabled,
  }) async {
    final response = await _dio.put<Map<String, dynamic>>(
      '/notifications/preferences',
      data: {'event': event, 'channel': channel, 'enabled': enabled},
    );
    return response.data ?? const <String, dynamic>{};
  }
}
