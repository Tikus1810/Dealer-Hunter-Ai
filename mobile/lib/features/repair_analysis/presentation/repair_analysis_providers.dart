import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/di/providers.dart';
import '../data/repair_api.dart';
import '../data/repair_repository_impl.dart';
import '../domain/repair_report.dart';
import '../domain/repair_repository.dart';
import 'repair_analysis_controller.dart';

final repairApiProvider = Provider<RepairApi>((ref) => RepairApi(ref.watch(dioProvider)));

final repairRepositoryProvider = Provider<RepairRepository>((ref) {
  return RepairRepositoryImpl(
    api: ref.watch(repairApiProvider),
    errorMapper: ref.watch(errorMapperProvider),
  );
});

final repairAnalysisControllerProvider = StateNotifierProvider.autoDispose
    .family<RepairAnalysisController, AsyncValue<RepairReport?>, String>((ref, offerId) {
  return RepairAnalysisController(ref.watch(repairRepositoryProvider), offerId);
});
