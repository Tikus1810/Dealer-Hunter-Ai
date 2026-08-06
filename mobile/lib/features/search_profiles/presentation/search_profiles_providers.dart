import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/di/providers.dart';
import '../data/search_profiles_api.dart';
import '../data/search_profiles_repository_impl.dart';
import '../domain/search_profile.dart';
import '../domain/search_profiles_repository.dart';
import 'search_profiles_controller.dart';

final searchProfilesApiProvider = Provider<SearchProfilesApi>(
  (ref) => SearchProfilesApi(ref.watch(dioProvider)),
);

final searchProfilesRepositoryProvider = Provider<SearchProfilesRepository>((ref) {
  return SearchProfilesRepositoryImpl(
    api: ref.watch(searchProfilesApiProvider),
    errorMapper: ref.watch(errorMapperProvider),
  );
});

final searchProfilesControllerProvider =
    StateNotifierProvider<SearchProfilesController, AsyncValue<List<SearchProfile>>>((ref) {
  return SearchProfilesController(ref.watch(searchProfilesRepositoryProvider));
});
