import 'package:dio/dio.dart';

import '../../../core/error/error_mapper.dart';
import '../domain/notification.dart';
import '../domain/notification_preference.dart';
import '../domain/notifications_repository.dart';
import 'notifications_api.dart';

class NotificationsRepositoryImpl implements NotificationsRepository {
  const NotificationsRepositoryImpl({
    required NotificationsApi api,
    required ErrorMapper errorMapper,
  })  : _api = api,
        _errorMapper = errorMapper;

  final NotificationsApi _api;
  final ErrorMapper _errorMapper;

  static const _pageSize = 100;

  @override
  Future<List<AppNotification>> listAllNotifications() async {
    try {
      final all = <AppNotification>[];
      var page = 1;
      while (true) {
        final body = await _api.listNotifications(page: page, pageSize: _pageSize);
        final items = (body['items'] as List<dynamic>? ?? const [])
            .map((e) => AppNotification.fromJson(e as Map<String, dynamic>))
            .toList();
        all.addAll(items);
        final total = body['total'] as int? ?? all.length;
        if (all.length >= total || items.isEmpty) break;
        page++;
      }
      return all;
    } on DioException catch (e) {
      throw _errorMapper.mapDioException(e);
    }
  }

  @override
  Future<void> markRead(String notificationId) async {
    try {
      await _api.markRead(notificationId);
    } on DioException catch (e) {
      throw _errorMapper.mapDioException(e);
    }
  }

  @override
  Future<List<NotificationPreference>> getPreferences() async {
    try {
      final rawList = await _api.getPreferences();
      return rawList
          .map((e) => NotificationPreference.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw _errorMapper.mapDioException(e);
    }
  }

  @override
  Future<NotificationPreference> setPreference({
    required String event,
    required String channel,
    required bool enabled,
  }) async {
    try {
      final body = await _api.setPreference(event: event, channel: channel, enabled: enabled);
      return NotificationPreference.fromJson(body);
    } on DioException catch (e) {
      throw _errorMapper.mapDioException(e);
    }
  }
}
