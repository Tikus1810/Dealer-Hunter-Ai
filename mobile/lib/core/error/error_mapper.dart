import 'package:dio/dio.dart';

import 'app_exception.dart';

/// Translates transport-level failures (`DioException`) into the app's
/// unified `AppException`. Data repositories are the only callers — no
/// widget should ever catch a `DioException` directly.
class ErrorMapper {
  const ErrorMapper();

  AppException mapDioException(DioException error) {
    final fromBody = _mapErrorResponseBody(error);
    if (fromBody != null) return fromBody;

    switch (error.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
      case DioExceptionType.transformTimeout:
      case DioExceptionType.connectionError:
        return AppException.network();
      case DioExceptionType.badCertificate:
      case DioExceptionType.badResponse:
      case DioExceptionType.cancel:
      case DioExceptionType.unknown:
        return AppException.unknown(error.message);
    }
  }

  /// The backend always responds with `{code, message, details,
  /// correlation_id}` for `DomainError`s (Band 10's unified error model) —
  /// prefer that over a generic transport-error message whenever present.
  AppException? _mapErrorResponseBody(DioException error) {
    final data = error.response?.data;
    if (data is! Map<String, dynamic>) return null;
    final code = data['code'];
    final message = data['message'];
    if (code is! String || message is! String) return null;

    final details = data['details'];
    final correlationId = data['correlation_id'];
    return AppException(
      code: code,
      message: message,
      details: details is Map<String, dynamic> ? details : null,
      correlationId: correlationId is String ? correlationId : null,
      statusCode: error.response?.statusCode,
    );
  }
}
