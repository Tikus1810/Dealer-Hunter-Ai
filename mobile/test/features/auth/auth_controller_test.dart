import 'package:deal_hunter_ai/features/auth/domain/auth_repository.dart';
import 'package:deal_hunter_ai/features/auth/presentation/auth_controller.dart';
import 'package:flutter_test/flutter_test.dart';

class _FakeAuthRepository implements AuthRepository {
  _FakeAuthRepository({this.hasSession = false, this.failWith});

  bool hasSession;
  Object? failWith;
  bool loginCalled = false;
  bool registerCalled = false;
  bool logoutCalled = false;

  @override
  Future<bool> hasValidSession() async => hasSession;

  @override
  Future<void> login({required String email, required String password}) async {
    loginCalled = true;
    if (failWith != null) throw failWith!;
    hasSession = true;
  }

  @override
  Future<void> register({required String email, required String password}) async {
    registerCalled = true;
    if (failWith != null) throw failWith!;
  }

  @override
  Future<void> logout() async {
    logoutCalled = true;
    hasSession = false;
  }
}

/// `AuthController`'s constructor kicks off an async `_restoreSession()`
/// call; flushing a zero-duration `Future.delayed` lets that microtask
/// chain settle before assertions run.
Future<void> _flushMicrotasks() => Future<void>.delayed(Duration.zero);

void main() {
  test('restores session as unauthenticated when no token is stored', () async {
    final repository = _FakeAuthRepository(hasSession: false);
    final controller = AuthController(repository);

    await _flushMicrotasks();

    expect(controller.state.valueOrNull, false);
  });

  test('restores session as authenticated when a token is stored', () async {
    final repository = _FakeAuthRepository(hasSession: true);
    final controller = AuthController(repository);

    await _flushMicrotasks();

    expect(controller.state.valueOrNull, true);
  });

  test('login sets state to authenticated on success', () async {
    final repository = _FakeAuthRepository(hasSession: false);
    final controller = AuthController(repository);
    await _flushMicrotasks();

    await controller.login(email: 'a@b.com', password: 'secret123');

    expect(repository.loginCalled, true);
    expect(controller.state.valueOrNull, true);
  });

  test('login surfaces a failure as AsyncError without throwing', () async {
    final repository = _FakeAuthRepository(
      hasSession: false,
      failWith: Exception('bad credentials'),
    );
    final controller = AuthController(repository);
    await _flushMicrotasks();

    await controller.login(email: 'a@b.com', password: 'wrong');

    expect(controller.state.hasError, true);
  });

  test('register calls register then login on success', () async {
    final repository = _FakeAuthRepository(hasSession: false);
    final controller = AuthController(repository);
    await _flushMicrotasks();

    await controller.register(email: 'a@b.com', password: 'secret123');

    expect(repository.registerCalled, true);
    expect(repository.loginCalled, true);
    expect(controller.state.valueOrNull, true);
  });

  test('logout clears authenticated state', () async {
    final repository = _FakeAuthRepository(hasSession: true);
    final controller = AuthController(repository);
    await _flushMicrotasks();

    await controller.logout();

    expect(repository.logoutCalled, true);
    expect(controller.state.valueOrNull, false);
  });
}
