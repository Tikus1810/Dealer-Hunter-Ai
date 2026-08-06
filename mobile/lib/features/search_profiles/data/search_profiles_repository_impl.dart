import 'package:dio/dio.dart';

import '../../../core/error/error_mapper.dart';
import '../domain/search_profile.dart';
import '../domain/search_profiles_repository.dart';
import 'search_profiles_api.dart';

class SearchProfilesRepositoryImpl implements SearchProfilesRepository {
  const SearchProfilesRepositoryImpl({
    required SearchProfilesApi api,
    required ErrorMapper errorMapper,
  })  : _api = api,
        _errorMapper = errorMapper;

  final SearchProfilesApi _api;
  final ErrorMapper _errorMapper;

  @override
  Future<List<SearchProfile>> listMyProfiles() async {
    try {
      final rawList = await _api.listMyProfiles();
      return rawList.map((e) => SearchProfile.fromJson(e as Map<String, dynamic>)).toList();
    } on DioException catch (e) {
      throw _errorMapper.mapDioException(e);
    }
  }

  @override
  Future<SearchProfile> createProfile({
    required String name,
    required String category,
    String? keywords,
    double? minPrice,
    double? maxPrice,
    int? minDealScore,
    bool notifyOnMatch = true,
  }) async {
    try {
      final body = await _api.createProfile({
        'name': name,
        'category': category,
        'keywords': keywords,
        'min_price': minPrice,
        'max_price': maxPrice,
        'min_deal_score': minDealScore,
        'notify_on_match': notifyOnMatch,
      });
      return SearchProfile.fromJson(body);
    } on DioException catch (e) {
      throw _errorMapper.mapDioException(e);
    }
  }

  @override
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
  }) async {
    try {
      final body = await _api.updateProfile(profileId, {
        'name': name,
        'category': category,
        'keywords': keywords,
        'min_price': minPrice,
        'max_price': maxPrice,
        'min_deal_score': minDealScore,
        'notify_on_match': notifyOnMatch,
        'is_active': isActive,
      });
      return SearchProfile.fromJson(body);
    } on DioException catch (e) {
      throw _errorMapper.mapDioException(e);
    }
  }

  @override
  Future<void> deleteProfile(String profileId) async {
    try {
      await _api.deleteProfile(profileId);
    } on DioException catch (e) {
      throw _errorMapper.mapDioException(e);
    }
  }
}
