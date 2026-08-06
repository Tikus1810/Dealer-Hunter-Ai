import 'package:deal_hunter_ai/features/favorites/domain/favorite.dart';
import 'package:deal_hunter_ai/features/favorites/domain/favorites_repository.dart';
import 'package:deal_hunter_ai/features/favorites/presentation/favorites_controller.dart';
import 'package:flutter_test/flutter_test.dart';

class _FakeFavoritesRepository implements FavoritesRepository {
  _FakeFavoritesRepository({List<Favorite>? initial}) : _favorites = List.of(initial ?? const []);

  final List<Favorite> _favorites;
  Object? failAddWith;
  Object? failRemoveWith;

  @override
  Future<List<Favorite>> listAllFavorites() async => List.of(_favorites);

  @override
  Future<Favorite> addFavorite(String offerId) async {
    if (failAddWith != null) throw failAddWith!;
    final created = Favorite(id: 'fav-$offerId', offerId: offerId);
    _favorites.add(created);
    return created;
  }

  @override
  Future<void> removeFavorite(String offerId) async {
    if (failRemoveWith != null) throw failRemoveWith!;
    _favorites.removeWhere((favorite) => favorite.offerId == offerId);
  }
}

Future<void> _flushMicrotasks() => Future<void>.delayed(Duration.zero);

void main() {
  test('loads the initial favorites list on construction', () async {
    final repository = _FakeFavoritesRepository(
      initial: [const Favorite(id: 'fav-1', offerId: 'offer-1')],
    );
    final controller = FavoritesController(repository);
    await _flushMicrotasks();

    expect(controller.isFavorited('offer-1'), true);
    expect(controller.isFavorited('offer-2'), false);
  });

  test('toggle adds a favorite that was not there', () async {
    final repository = _FakeFavoritesRepository();
    final controller = FavoritesController(repository);
    await _flushMicrotasks();

    await controller.toggle('offer-1');

    expect(controller.isFavorited('offer-1'), true);
  });

  test('toggle removes a favorite that was already there', () async {
    final repository = _FakeFavoritesRepository(
      initial: [const Favorite(id: 'fav-1', offerId: 'offer-1')],
    );
    final controller = FavoritesController(repository);
    await _flushMicrotasks();

    await controller.toggle('offer-1');

    expect(controller.isFavorited('offer-1'), false);
  });

  test('a failed removal reverts the optimistic update', () async {
    final repository = _FakeFavoritesRepository(
      initial: [const Favorite(id: 'fav-1', offerId: 'offer-1')],
    )..failRemoveWith = Exception('network error');
    final controller = FavoritesController(repository);
    await _flushMicrotasks();

    await expectLater(controller.toggle('offer-1'), throwsA(isA<Exception>()));

    expect(controller.isFavorited('offer-1'), true); // reverted
  });
}
