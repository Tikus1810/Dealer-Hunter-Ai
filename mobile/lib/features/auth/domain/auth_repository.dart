/// Public interface of the `auth` feature's data layer — presentation code
/// (`AuthController`) depends only on this, never on `AuthApi`/Dio/secure
/// storage directly (Band 04: Clean Architecture, Repository Pattern).
abstract class AuthRepository {
  Future<void> register({required String email, required String password});

  Future<void> login({required String email, required String password});

  Future<void> logout();

  /// v1 simplification: checks only whether an access token is stored
  /// locally, not whether it's still valid (no client-side JWT expiry
  /// check). `AuthInterceptor`'s refresh-on-401 flow is the real source of
  /// truth once an actual API call is made.
  Future<bool> hasValidSession();
}
