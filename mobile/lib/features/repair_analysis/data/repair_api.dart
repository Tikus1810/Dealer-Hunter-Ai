import 'package:dio/dio.dart';

/// Thin wrapper over `POST /api/v1/offers/{offerId}/repair-report`
/// (`backend/app/modules/repair/presentation/router.py`).
class RepairApi {
  const RepairApi(this._dio);

  final Dio _dio;

  Future<Map<String, dynamic>> analyze(
    String offerId, {
    required List<String> reportedDefects,
  }) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/offers/$offerId/repair-report',
      data: {'reported_defects': reportedDefects},
    );
    return response.data ?? const <String, dynamic>{};
  }
}
