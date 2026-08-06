import 'package:dio/dio.dart';

import '../../../core/error/error_mapper.dart';
import '../domain/favorite.dart';
import '../domain/favorites_repository.dart';
import 'favorites_api.dart';

class FavoritesRepositoryImpl implements FavoritesRepository {
  const FavoritesRepositoryImpl({required FavoritesApi api, required ErrorMapper errorMapper})
      : _api = api,
        _errorMapper = errorMapper;

  final FavoritesApi _api;
  final ErrorMapper _errorMapper;

  static const _pageSize = 100;

  @override
  Future<List<Favorite>> listAllFavorites() async {
    try {
      final all = <Favorite>[];
      var page = 1;
      while (true) {
        final body = await _api.listFavorites(page: page, pageSize: _pageSize);
        final items = (body['items'] as List<dynamic>? ?? const [])
            .map((e) => Favorite.fromJson(e as Map<String, dynamic>))
            .toList();
        all.addAll(items);
        final total = body['total'] as int? ?? all.length;
        if (all.length >= total || items.isEmpty) break;
        page++;
      }
      return all;
    } on DioException catch (e) {
      throw _errorMapper.mapDioException(e);
    }
  }

  @override
  Future<Favorite> addFavorite(String offerId) async {
    try {
      final body = await _api.addFavorite(offerId);
      return Favorite.fromJson(body);
    } on DioException catch (e) {
      throw _errorMapper.mapDioException(e);
    }
  }

  @override
  Future<void> removeFavorite(String offerId) async {
    try {
      await _api.removeFavorite(offerId);
    } on DioException catch (e) {
      throw _errorMapper.mapDioException(e);
    }
  }
}
