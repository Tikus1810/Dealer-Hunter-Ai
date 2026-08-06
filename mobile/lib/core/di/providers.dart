import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../config/app_config.dart';
import '../error/error_mapper.dart';
import '../network/dio_factory.dart';
import '../network/token_storage.dart';

/// Cross-cutting dependency injection (Band 04: "Dependency Injection").
/// Feature modules build their own providers on top of these — see
/// `features/auth/presentation/auth_providers.dart` for the pattern.
final appConfigProvider = Provider<AppConfig>((ref) => AppConfig.fromEnvironment());

final secureStorageProvider = Provider<FlutterSecureStorage>(
  (ref) => const FlutterSecureStorage(),
);

final tokenStorageProvider = Provider<TokenStorage>(
  (ref) => TokenStorage(ref.watch(secureStorageProvider)),
);

final errorMapperProvider = Provider<ErrorMapper>((ref) => const ErrorMapper());

final dioProvider = Provider<Dio>((ref) {
  return createApiDio(
    config: ref.watch(appConfigProvider),
    tokenStorage: ref.watch(tokenStorageProvider),
  );
});
