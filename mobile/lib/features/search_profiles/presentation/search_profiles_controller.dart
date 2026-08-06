import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../domain/search_profile.dart';
import '../domain/search_profiles_repository.dart';

class SearchProfilesController extends StateNotifier<AsyncValue<List<SearchProfile>>> {
  SearchProfilesController(this._repository) : super(const AsyncValue.loading()) {
    refresh();
  }

  final SearchProfilesRepository _repository;

  Future<void> refresh() async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(_repository.listMyProfiles);
  }

  Future<void> create({
    required String name,
    required String category,
    String? keywords,
    double? minPrice,
    double? maxPrice,
    int? minDealScore,
    bool notifyOnMatch = true,
  }) async {
    await _repository.createProfile(
      name: name,
      category: category,
      keywords: keywords,
      minPrice: minPrice,
      maxPrice: maxPrice,
      minDealScore: minDealScore,
      notifyOnMatch: notifyOnMatch,
    );
    await refresh();
  }

  Future<void> update(
    String profileId, {
    String? name,
    String? category,
    String? keywords,
    double? minPrice,
    double? maxPrice,
    int? minDealScore,
    bool? notifyOnMatch,
    bool? isActive,
  }) async {
    await _repository.updateProfile(
      profileId,
      name: name,
      category: category,
      keywords: keywords,
      minPrice: minPrice,
      maxPrice: maxPrice,
      minDealScore: minDealScore,
      notifyOnMatch: notifyOnMatch,
      isActive: isActive,
    );
    await refresh();
  }

  Future<void> delete(String profileId) async {
    await _repository.deleteProfile(profileId);
    await refresh();
  }
}
