import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/di/providers.dart';
import '../data/auth_api.dart';
import '../data/auth_repository_impl.dart';
import '../domain/auth_repository.dart';
import 'auth_controller.dart';

final authApiProvider = Provider<AuthApi>((ref) => AuthApi(ref.watch(dioProvider)));

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  return AuthRepositoryImpl(
    api: ref.watch(authApiProvider),
    tokenStorage: ref.watch(tokenStorageProvider),
    errorMapper: ref.watch(errorMapperProvider),
  );
});

/// The single source of truth for "is anyone logged in right now" — the
/// router's redirect logic watches this (see `core/router/app_router.dart`).
final authControllerProvider = StateNotifierProvider<AuthController, AsyncValue<bool>>((ref) {
  return AuthController(ref.watch(authRepositoryProvider));
});
