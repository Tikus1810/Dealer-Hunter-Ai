import 'package:dio/dio.dart';

/// Retries transient network failures with a short linear backoff (Band
/// 04: "Retry policy"). Only retries connection-level failures — a real
/// HTTP error response (4xx/5xx) is never retried here, since retrying a
/// 400 or 404 would just repeat the same failure.
class RetryInterceptor extends Interceptor {
  RetryInterceptor({
    required this.dio,
    this.maxRetries = 2,
    this.retryDelay = const Duration(milliseconds: 500),
  });

  final Dio dio;
  final int maxRetries;
  final Duration retryDelay;

  static const _retryableTypes = {
    DioExceptionType.connectionTimeout,
    DioExceptionType.sendTimeout,
    DioExceptionType.receiveTimeout,
    DioExceptionType.connectionError,
  };

  @override
  Future<void> onError(DioException err, ErrorInterceptorHandler handler) async {
    final attempt = err.requestOptions.extra['dh_retry_attempt'] as int? ?? 0;
    final isRetryable = _retryableTypes.contains(err.type);

    if (!isRetryable || attempt >= maxRetries) {
      handler.next(err);
      return;
    }

    await Future<void>.delayed(retryDelay * (attempt + 1));
    final retryOptions = err.requestOptions..extra['dh_retry_attempt'] = attempt + 1;
    try {
      final response = await dio.fetch<dynamic>(retryOptions);
      handler.resolve(response);
    } on DioException catch (retryError) {
      handler.next(retryError);
    }
  }
}
