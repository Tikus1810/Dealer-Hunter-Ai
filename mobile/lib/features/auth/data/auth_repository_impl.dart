import 'package:dio/dio.dart';

import '../../../core/error/app_exception.dart';
import '../../../core/error/error_mapper.dart';
import '../../../core/network/token_storage.dart';
import '../domain/auth_repository.dart';
import 'auth_api.dart';

class AuthRepositoryImpl implements AuthRepository {
  const AuthRepositoryImpl({
    required AuthApi api,
    required TokenStorage tokenStorage,
    required ErrorMapper errorMapper,
  })  : _api = api,
        _tokenStorage = tokenStorage,
        _errorMapper = errorMapper;

  final AuthApi _api;
  final TokenStorage _tokenStorage;
  final ErrorMapper _errorMapper;

  @override
  Future<void> register({required String email, required String password}) async {
    try {
      await _api.register(email: email, password: password);
    } on DioException catch (e) {
      throw _errorMapper.mapDioException(e);
    }
  }

  @override
  Future<void> login({required String email, required String password}) async {
    try {
      final body = await _api.login(email: email, password: password);
      final accessToken = body['access_token'];
      final refreshToken = body['refresh_token'];
      if (accessToken is! String || refreshToken is! String) {
        throw const AppException(
          code: 'invalid_response',
          message: 'Unerwartete Antwort vom Server.',
        );
      }
      await _tokenStorage.saveTokens(accessToken: accessToken, refreshToken: refreshToken);
    } on DioException catch (e) {
      throw _errorMapper.mapDioException(e);
    }
  }

  @override
  Future<void> logout() async {
    final refreshToken = await _tokenStorage.readRefreshToken();
    try {
      if (refreshToken != null) {
        await _api.logout(refreshToken: refreshToken);
      }
    } on DioException {
      // Best-effort: even if server-side revocation fails, always clear
      // local tokens so the user is logged out on this device.
    } finally {
      await _tokenStorage.clear();
    }
  }

  @override
  Future<bool> hasValidSession() async {
    final accessToken = await _tokenStorage.readAccessToken();
    return accessToken != null;
  }
}
