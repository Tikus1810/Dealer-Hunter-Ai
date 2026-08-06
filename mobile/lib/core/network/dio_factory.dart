import 'package:dio/dio.dart';

import '../config/app_config.dart';
import 'auth_interceptor.dart';
import 'retry_interceptor.dart';
import 'token_storage.dart';

/// Builds the single `Dio` instance the whole app shares, wired with the
/// interceptor pipeline in the order that matters (Band 04: "Central error
/// handling"): auth (token attach + refresh-and-retry-once on 401) runs
/// before the generic retry policy, so a 401 is never mistaken for a
/// retryable network blip.
Dio createApiDio({required AppConfig config, required TokenStorage tokenStorage}) {
  final dio = Dio(
    BaseOptions(
      baseUrl: config.apiBaseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 15),
      headers: const {'Content-Type': 'application/json'},
    ),
  );
  dio.interceptors.addAll([
    AuthInterceptor(dio: dio, tokenStorage: tokenStorage),
    RetryInterceptor(dio: dio),
  ]);
  return dio;
}
