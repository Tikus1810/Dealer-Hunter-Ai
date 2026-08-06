import 'package:dio/dio.dart';

/// Thin wrapper over `GET /api/v1/offers/{offerId}/deal-score`
/// (`backend/app/modules/scoring/presentation/router.py`).
class DealScoreApi {
  const DealScoreApi(this._dio);

  final Dio _dio;

  Future<Map<String, dynamic>> getDealScore(String offerId) async {
    final response = await _dio.get<Map<String, dynamic>>('/offers/$offerId/deal-score');
    return response.data ?? const <String, dynamic>{};
  }
}
