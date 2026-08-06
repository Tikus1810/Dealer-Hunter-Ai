import 'search_profile.dart';

abstract class SearchProfilesRepository {
  Future<List<SearchProfile>> listMyProfiles();

  Future<SearchProfile> createProfile({
    required String name,
    required String category,
    String? keywords,
    double? minPrice,
    double? maxPrice,
    int? minDealScore,
    bool notifyOnMatch = true,
  });

  Future<SearchProfile> updateProfile(
    String profileId, {
    String? name,
    String? category,
    String? keywords,
    double? minPrice,
    double? maxPrice,
    int? minDealScore,
    bool? notifyOnMatch,
    bool? isActive,
  });

  Future<void> deleteProfile(String profileId);
}
