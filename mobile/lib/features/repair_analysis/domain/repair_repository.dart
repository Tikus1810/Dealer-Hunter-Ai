import 'repair_report.dart';

abstract class RepairRepository {
  /// Computes (and, server-side, persists) a fresh report — mirrors
  /// `POST /api/v1/offers/{offerId}/repair-report` not being idempotent.
  Future<RepairReport> analyze(String offerId, {required List<String> reportedDefects});
}
