import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/di/providers.dart';
import '../data/favorites_api.dart';
import '../data/favorites_repository_impl.dart';
import '../domain/favorite.dart';
import '../domain/favorites_repository.dart';
import 'favorites_controller.dart';

final favoritesApiProvider = Provider<FavoritesApi>((ref) => FavoritesApi(ref.watch(dioProvider)));

final favoritesRepositoryProvider = Provider<FavoritesRepository>((ref) {
  return FavoritesRepositoryImpl(
    api: ref.watch(favoritesApiProvider),
    errorMapper: ref.watch(errorMapperProvider),
  );
});

final favoritesControllerProvider =
    StateNotifierProvider<FavoritesController, AsyncValue<List<Favorite>>>((ref) {
  return FavoritesController(ref.watch(favoritesRepositoryProvider));
});
