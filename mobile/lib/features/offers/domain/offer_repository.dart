import 'offer.dart';
import 'offer_category.dart';

abstract class OfferRepository {
  Future<OfferPage> listOffers({
    required OfferCategory category,
    required int page,
    int pageSize = 20,
  });

  Future<Offer> getOffer(String offerId);
}
