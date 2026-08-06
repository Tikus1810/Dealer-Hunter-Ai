import 'package:dio/dio.dart';

import 'token_storage.dart';

/// Attaches the stored access token to every request, and — on a 401 —
/// attempts exactly one silent token refresh before retrying the original
/// request once (Band 04: "Automatic token refresh").
///
/// v1 simplification: concurrent 401s during an in-flight refresh don't
/// queue and wait for it, they just fail through — a burst of parallel
/// requests right when the access token expires can surface more than one
/// login prompt instead of one. Fine for a foundation-stage app; revisit
/// with a request queue if that proves annoying in practice.
class AuthInterceptor extends Interceptor {
  AuthInterceptor({required this.dio, required this.tokenStorage});

  final Dio dio;
  final TokenStorage tokenStorage;

  bool _isRefreshing = false;

  static const _unauthenticatedPaths = ['/auth/login', '/auth/register', '/auth/refresh'];

  @override
  Future<void> onRequest(RequestOptions options, RequestInterceptorHandler handler) async {
    final needsAuth = !_unauthenticatedPaths.any((path) => options.path.contains(path));
    if (needsAuth) {
      final accessToken = await tokenStorage.readAccessToken();
      if (accessToken != null) {
        options.headers['Authorization'] = 'Bearer $accessToken';
      }
    }
    handler.next(options);
  }

  @override
  Future<void> onError(DioException err, ErrorInterceptorHandler handler) async {
    final isUnauthorized = err.response?.statusCode == 401;
    final isRefreshCall = err.requestOptions.path.contains('/auth/refresh');
    final alreadyRetried = err.requestOptions.extra['dh_retried_after_refresh'] == true;

    if (!isUnauthorized || isRefreshCall || alreadyRetried || _isRefreshing) {
      handler.next(err);
      return;
    }

    _isRefreshing = true;
    try {
      final refreshToken = await tokenStorage.readRefreshToken();
      if (refreshToken == null) {
        await tokenStorage.clear();
        handler.next(err);
        return;
      }

      // A separate, interceptor-free Dio instance for the refresh call
      // itself — reusing `dio` would re-enter this same interceptor chain.
      final refreshDio = Dio(BaseOptions(baseUrl: dio.options.baseUrl));
      final refreshResponse = await refreshDio.post<Map<String, dynamic>>(
        '/auth/refresh',
        data: {'refresh_token': refreshToken},
      );
      final newAccessToken = refreshResponse.data?['access_token'];
      final newRefreshToken = refreshResponse.data?['refresh_token'];
      if (newAccessToken is! String || newRefreshToken is! String) {
        await tokenStorage.clear();
        handler.next(err);
        return;
      }
      await tokenStorage.saveTokens(accessToken: newAccessToken, refreshToken: newRefreshToken);

      final retryOptions = err.requestOptions
        ..headers['Authorization'] = 'Bearer $newAccessToken'
        ..extra['dh_retried_after_refresh'] = true;
      final retryResponse = await dio.fetch<dynamic>(retryOptions);
      handler.resolve(retryResponse);
    } catch (_) {
      // Any failure during refresh (network, secure storage, malformed
      // response) means "the session can't be salvaged right now" — clear
      // it and let the original 401 propagate rather than surfacing a
      // different, more confusing error.
      await tokenStorage.clear();
      handler.next(err);
    } finally {
      _isRefreshing = false;
    }
  }
}
