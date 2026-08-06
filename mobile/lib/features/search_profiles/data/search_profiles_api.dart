import 'package:dio/dio.dart';

/// Thin wrapper over `/api/v1/search-profiles`
/// (`backend/app/modules/search/presentation/router.py`).
class SearchProfilesApi {
  const SearchProfilesApi(this._dio);

  final Dio _dio;

  Future<List<dynamic>> listMyProfiles() async {
    final response = await _dio.get<List<dynamic>>('/search-profiles');
    return response.data ?? const [];
  }

  Future<Map<String, dynamic>> createProfile(Map<String, dynamic> body) async {
    final response = await _dio.post<Map<String, dynamic>>('/search-profiles', data: body);
    return response.data ?? const <String, dynamic>{};
  }

  Future<Map<String, dynamic>> updateProfile(String profileId, Map<String, dynamic> body) async {
    final response = await _dio.patch<Map<String, dynamic>>(
      '/search-profiles/$profileId',
      data: body,
    );
    return response.data ?? const <String, dynamic>{};
  }

  Future<void> deleteProfile(String profileId) async {
    await _dio.delete<void>('/search-profiles/$profileId');
  }
}
