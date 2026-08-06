import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Encrypted on-device storage for the JWT access/refresh token pair
/// (Band 04: networking requirements imply persisted auth across app
/// restarts). Every read/write goes through here — nothing else should
/// touch `FlutterSecureStorage` directly.
class TokenStorage {
  const TokenStorage(this._storage);

  final FlutterSecureStorage _storage;

  static const _accessTokenKey = 'dh_access_token';
  static const _refreshTokenKey = 'dh_refresh_token';

  Future<String?> readAccessToken() => _storage.read(key: _accessTokenKey);

  Future<String?> readRefreshToken() => _storage.read(key: _refreshTokenKey);

  Future<void> saveTokens({required String accessToken, required String refreshToken}) async {
    await _storage.write(key: _accessTokenKey, value: accessToken);
    await _storage.write(key: _refreshTokenKey, value: refreshToken);
  }

  Future<void> clear() async {
    await _storage.delete(key: _accessTokenKey);
    await _storage.delete(key: _refreshTokenKey);
  }
}
