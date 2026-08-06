import 'package:dio/dio.dart';

/// Thin wrapper over the backend's `/api/v1/auth/*` endpoints (see
/// `backend/app/modules/auth/presentation/router.py`). Returns raw decoded
/// JSON — `AuthRepositoryImpl` is responsible for turning that into
/// something the rest of the app understands.
class AuthApi {
  const AuthApi(this._dio);

  final Dio _dio;

  Future<Map<String, dynamic>> register({required String email, required String password}) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/auth/register',
      data: {'email': email, 'password': password},
    );
    return response.data ?? const <String, dynamic>{};
  }

  Future<Map<String, dynamic>> login({required String email, required String password}) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/auth/login',
      data: {'email': email, 'password': password},
    );
    return response.data ?? const <String, dynamic>{};
  }

  Future<void> logout({required String refreshToken}) async {
    await _dio.post<void>('/auth/logout', data: {'refresh_token': refreshToken});
  }
}
