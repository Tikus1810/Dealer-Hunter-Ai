import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/error/app_exception.dart';
import '../../../core/router/route_paths.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/widgets/app_content_bounds.dart';
import '../../../core/widgets/empty_view.dart';
import '../../../core/widgets/error_view.dart';
import '../../../core/widgets/loading_view.dart';
import '../../offers/presentation/offer_providers.dart';
import '../../offers/presentation/widgets/offer_card.dart';
import 'favorites_providers.dart';

/// Backed by `GET /api/v1/favorites`. Note the backend only returns
/// `{id, offer_id, created_at}` per favorite — this screen fetches each
/// favorited offer's own details individually (`offerDetailProvider`,
/// which is itself cached/shared with the offer list and detail screens)
/// rather than needing a dedicated batch endpoint. Fine at the list sizes
/// a "favorites" feature realistically has; revisit if that changes.
class FavoritesScreen extends ConsumerWidget {
  const FavoritesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final favoritesAsync = ref.watch(favoritesControllerProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Favoriten')),
      body: AppContentBounds(
        child: favoritesAsync.when(
          data: (favorites) {
            if (favorites.isEmpty) {
              return const EmptyView(
                icon: CupertinoIcons.heart,
                message: 'Noch keine Favoriten gespeichert.',
              );
            }
            return RefreshIndicator(
              onRefresh: () => ref.read(favoritesControllerProvider.notifier).refresh(),
              child: ListView.builder(
                padding:
                    const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: AppSpacing.sm),
                itemCount: favorites.length,
                itemBuilder: (context, index) => _FavoriteRow(offerId: favorites[index].offerId),
              ),
            );
          },
          loading: () => const LoadingView(),
          error: (error, stackTrace) => ErrorView(
            message: _errorMessage(error),
            onRetry: () => ref.read(favoritesControllerProvider.notifier).refresh(),
          ),
        ),
      ),
    );
  }

  String _errorMessage(Object error) {
    if (error is AppException) return error.message;
    return 'Ein unerwarteter Fehler ist aufgetreten.';
  }
}

class _FavoriteRow extends ConsumerWidget {
  const _FavoriteRow({required this.offerId});

  final String offerId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final offerAsync = ref.watch(offerDetailProvider(offerId));

    return offerAsync.when(
      data: (offer) => OfferCard(
        offer: offer,
        onTap: () => context.push(RoutePaths.offerDetailPath(offerId)),
      ),
      loading: () => const Card(
        child: Padding(
          padding: EdgeInsets.all(AppSpacing.md),
          child: LinearProgressIndicator(),
        ),
      ),
      // An offer that's since been deleted/deactivated shouldn't block the
      // rest of the favorites list from rendering.
      error: (error, stackTrace) => const SizedBox.shrink(),
    );
  }
}
