import 'package:dio/dio.dart';

import '../../../core/error/error_mapper.dart';
import '../domain/offer.dart';
import '../domain/offer_category.dart';
import '../domain/offer_repository.dart';
import 'offer_api.dart';

class OfferRepositoryImpl implements OfferRepository {
  const OfferRepositoryImpl({required OfferApi api, required ErrorMapper errorMapper})
      : _api = api,
        _errorMapper = errorMapper;

  final OfferApi _api;
  final ErrorMapper _errorMapper;

  @override
  Future<OfferPage> listOffers({
    required OfferCategory category,
    required int page,
    int pageSize = 20,
  }) async {
    try {
      final body = await _api.listOffers(
        category: category.apiValue,
        page: page,
        pageSize: pageSize,
      );
      return OfferPage.fromJson(body);
    } on DioException catch (e) {
      throw _errorMapper.mapDioException(e);
    }
  }

  @override
  Future<Offer> getOffer(String offerId) async {
    try {
      final body = await _api.getOffer(offerId);
      return Offer.fromJson(body);
    } on DioException catch (e) {
      throw _errorMapper.mapDioException(e);
    }
  }
}
