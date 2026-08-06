import 'deal_score.dart';

abstract class DealScoreRepository {
  /// Computes (and, server-side, persists) a fresh score on every call —
  /// mirrors `GET /api/v1/offers/{offerId}/deal-score` not being a cache.
  Future<DealScore> getDealScore(String offerId);
}
