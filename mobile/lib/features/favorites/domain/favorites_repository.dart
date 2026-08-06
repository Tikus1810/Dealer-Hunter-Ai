import 'favorite.dart';

abstract class FavoritesRepository {
  /// Fetches every favorite across all pages (the favorites screen shows
  /// them all at once rather than paginating a typically-small list).
  Future<List<Favorite>> listAllFavorites();

  Future<Favorite> addFavorite(String offerId);

  Future<void> removeFavorite(String offerId);
}
