import 'package:dio/dio.dart';

/// Thin wrapper over `GET /api/v1/offers` and `GET /api/v1/offers/{id}`
/// (`backend/app/modules/offers/presentation/router.py`).
class OfferApi {
  const OfferApi(this._dio);

  final Dio _dio;

  Future<Map<String, dynamic>> listOffers({
    required String category,
    required int page,
    required int pageSize,
  }) async {
    final response = await _dio.get<Map<String, dynamic>>(
      '/offers',
      queryParameters: {'category': category, 'page': page, 'page_size': pageSize},
    );
    return response.data ?? const <String, dynamic>{};
  }

  Future<Map<String, dynamic>> getOffer(String offerId) async {
    final response = await _dio.get<Map<String, dynamic>>('/offers/$offerId');
    return response.data ?? const <String, dynamic>{};
  }
}
