import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/di/providers.dart';
import '../data/deal_score_api.dart';
import '../data/deal_score_repository_impl.dart';
import '../domain/deal_score.dart';
import '../domain/deal_score_repository.dart';

final dealScoreApiProvider = Provider<DealScoreApi>((ref) => DealScoreApi(ref.watch(dioProvider)));

final dealScoreRepositoryProvider = Provider<DealScoreRepository>((ref) {
  return DealScoreRepositoryImpl(
    api: ref.watch(dealScoreApiProvider),
    errorMapper: ref.watch(errorMapperProvider),
  );
});

final dealScoreProvider = FutureProvider.autoDispose.family<DealScore, String>((ref, offerId) {
  return ref.watch(dealScoreRepositoryProvider).getDealScore(offerId);
});
