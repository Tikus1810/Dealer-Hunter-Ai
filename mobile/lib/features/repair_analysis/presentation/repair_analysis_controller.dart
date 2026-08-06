import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../domain/repair_report.dart';
import '../domain/repair_repository.dart';

/// One controller instance per offer (see the `.family` provider below).
/// Starts at `AsyncValue.data(null)` — "not analyzed yet" — rather than
/// loading, since analysis only starts when the user asks for it (Band 04:
/// repair analysis is an on-demand action, not an automatic fetch, unlike
/// `dealScoreProvider`).
class RepairAnalysisController extends StateNotifier<AsyncValue<RepairReport?>> {
  RepairAnalysisController(this._repository, this._offerId) : super(const AsyncValue.data(null));

  final RepairRepository _repository;
  final String _offerId;

  Future<void> analyze({required List<String> reportedDefects}) async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(
      () => _repository.analyze(_offerId, reportedDefects: reportedDefects),
    );
  }
}
