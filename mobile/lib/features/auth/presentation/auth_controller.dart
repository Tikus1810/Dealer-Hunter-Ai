import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../domain/auth_repository.dart';

/// `state.value == true` means "has a session"; `false` means "logged
/// out"; `state.isLoading`/`state.hasError` drive UI feedback during an
/// in-flight login/register call (Band 04: "Separation of UI and business
/// logic" — no widget talks to `AuthRepository` directly).
class AuthController extends StateNotifier<AsyncValue<bool>> {
  AuthController(this._repository) : super(const AsyncValue.loading()) {
    _restoreSession();
  }

  final AuthRepository _repository;

  Future<void> _restoreSession() async {
    state = await AsyncValue.guard(() => _repository.hasValidSession());
  }

  Future<void> login({required String email, required String password}) async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(() async {
      await _repository.login(email: email, password: password);
      return true;
    });
  }

  Future<void> register({required String email, required String password}) async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(() async {
      await _repository.register(email: email, password: password);
      await _repository.login(email: email, password: password);
      return true;
    });
  }

  Future<void> logout() async {
    await _repository.logout();
    state = const AsyncValue.data(false);
  }
}
