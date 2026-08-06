import 'package:dio/dio.dart';

import '../../../core/error/error_mapper.dart';
import '../domain/repair_repository.dart';
import '../domain/repair_report.dart';
import 'repair_api.dart';

class RepairRepositoryImpl implements RepairRepository {
  const RepairRepositoryImpl({required RepairApi api, required ErrorMapper errorMapper})
      : _api = api,
        _errorMapper = errorMapper;

  final RepairApi _api;
  final ErrorMapper _errorMapper;

  @override
  Future<RepairReport> analyze(String offerId, {required List<String> reportedDefects}) async {
    try {
      final body = await _api.analyze(offerId, reportedDefects: reportedDefects);
      return RepairReport.fromJson(body);
    } on DioException catch (e) {
      throw _errorMapper.mapDioException(e);
    }
  }
}
