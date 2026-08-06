import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/error/app_exception.dart';
import '../domain/favorite.dart';
import '../domain/favorites_repository.dart';

/// Loads the user's full favorites list once and keeps it in memory,
/// exposing `isFavorited`/`toggle` so any screen (offer list, offer detail,
/// the favorites screen itself) can share one source of truth instead of
/// each re-fetching or duplicating favorite state.
class FavoritesController extends StateNotifier<AsyncValue<List<Favorite>>> {
  FavoritesController(this._repository) : super(const AsyncValue.loading()) {
    refresh();
  }

  final FavoritesRepository _repository;

  Future<void> refresh() async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(_repository.listAllFavorites);
  }

  bool isFavorited(String offerId) {
    return state.valueOrNull?.any((favorite) => favorite.offerId == offerId) ?? false;
  }

  /// Adds or removes the favorite, updating local state immediately
  /// (optimistic) so the UI doesn't wait on a round-trip for a checkmark to
  /// flip — reverts if the request fails.
  Future<void> toggle(String offerId) async {
    final current = state.valueOrNull;
    if (current == null) return;

    final alreadyFavorited = current.any((favorite) => favorite.offerId == offerId);
    if (alreadyFavorited) {
      state = AsyncValue.data(
        current.where((favorite) => favorite.offerId != offerId).toList(),
      );
      try {
        await _repository.removeFavorite(offerId);
      } catch (_) {
        state = AsyncValue.data(current); // revert
        rethrow;
      }
    } else {
      try {
        final created = await _repository.addFavorite(offerId);
        final latest = state.valueOrNull ?? current;
        state = AsyncValue.data([...latest, created]);
      } on AppException {
        rethrow;
      }
    }
  }
}
