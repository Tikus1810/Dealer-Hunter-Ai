import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/di/providers.dart';
import '../data/offer_api.dart';
import '../data/offer_repository_impl.dart';
import '../domain/offer.dart';
import '../domain/offer_category.dart';
import '../domain/offer_repository.dart';

final offerApiProvider = Provider<OfferApi>((ref) => OfferApi(ref.watch(dioProvider)));

final offerRepositoryProvider = Provider<OfferRepository>((ref) {
  return OfferRepositoryImpl(
    api: ref.watch(offerApiProvider),
    errorMapper: ref.watch(errorMapperProvider),
  );
});

/// The offer list screen's current filter/pagination — kept as plain
/// `StateProvider`s (not folded into the list controller) so other widgets
/// (e.g. a future filter chip row) can read/drive them independently.
final selectedOfferCategoryProvider = StateProvider<OfferCategory>(
  (ref) => OfferCategory.macbook,
);

final offerListPageProvider = StateProvider<int>((ref) => 1);

final offerListProvider = FutureProvider.autoDispose<OfferPage>((ref) {
  final category = ref.watch(selectedOfferCategoryProvider);
  final page = ref.watch(offerListPageProvider);
  return ref.watch(offerRepositoryProvider).listOffers(category: category, page: page);
});

final offerDetailProvider = FutureProvider.autoDispose.family<Offer, String>((ref, offerId) {
  return ref.watch(offerRepositoryProvider).getOffer(offerId);
});
