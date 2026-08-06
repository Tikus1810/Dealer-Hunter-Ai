import 'package:dio/dio.dart';

import '../../../core/error/error_mapper.dart';
import '../domain/deal_score.dart';
import '../domain/deal_score_repository.dart';
import 'deal_score_api.dart';

class DealScoreRepositoryImpl implements DealScoreRepository {
  const DealScoreRepositoryImpl({required DealScoreApi api, required ErrorMapper errorMapper})
      : _api = api,
        _errorMapper = errorMapper;

  final DealScoreApi _api;
  final ErrorMapper _errorMapper;

  @override
  Future<DealScore> getDealScore(String offerId) async {
    try {
      final body = await _api.getDealScore(offerId);
      return DealScore.fromJson(body);
    } on DioException catch (e) {
      throw _errorMapper.mapDioException(e);
    }
  }
}
