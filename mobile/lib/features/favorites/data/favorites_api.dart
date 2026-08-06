import 'package:dio/dio.dart';

/// Thin wrapper over `GET /api/v1/favorites` and
/// `POST/DELETE /api/v1/offers/{id}/favorite`
/// (`backend/app/modules/offers/presentation/router.py`).
class FavoritesApi {
  const FavoritesApi(this._dio);

  final Dio _dio;

  Future<Map<String, dynamic>> listFavorites({required int page, required int pageSize}) async {
    final response = await _dio.get<Map<String, dynamic>>(
      '/favorites',
      queryParameters: {'page': page, 'page_size': pageSize},
    );
    return response.data ?? const <String, dynamic>{};
  }

  Future<Map<String, dynamic>> addFavorite(String offerId) async {
    final response = await _dio.post<Map<String, dynamic>>('/offers/$offerId/favorite');
    return response.data ?? const <String, dynamic>{};
  }

  Future<void> removeFavorite(String offerId) async {
    await _dio.delete<void>('/offers/$offerId/favorite');
  }
}
