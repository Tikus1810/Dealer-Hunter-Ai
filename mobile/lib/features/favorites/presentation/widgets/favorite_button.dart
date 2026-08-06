import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/error/app_exception.dart';
import '../favorites_controller.dart';
import '../favorites_providers.dart';

/// A heart icon button reflecting (and toggling) whether an offer is in
/// the user's favorites — shared by the offer detail screen and, in
/// principle, any future list that needs the same affordance.
class FavoriteButton extends ConsumerWidget {
  const FavoriteButton({super.key, required this.offerId});

  final String offerId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final favoritesState = ref.watch(favoritesControllerProvider);
    final isFavorited = ref.read(favoritesControllerProvider.notifier).isFavorited(offerId);
    final isBusy = favoritesState.isLoading;

    return IconButton(
      tooltip: isFavorited ? 'Von Favoriten entfernen' : 'Zu Favoriten hinzufügen',
      icon: Icon(isFavorited ? Icons.favorite : Icons.favorite_border),
      color: isFavorited ? Theme.of(context).colorScheme.error : null,
      onPressed: isBusy
          ? null
          : () async {
              try {
                await ref.read(favoritesControllerProvider.notifier).toggle(offerId);
              } on AppException catch (e) {
                if (!context.mounted) return;
                ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
              }
            },
    );
  }
}
