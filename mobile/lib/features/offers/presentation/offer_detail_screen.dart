import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/error/app_exception.dart';
import '../../../core/router/route_paths.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/widgets/app_cupertino_dialog.dart';
import '../../../core/widgets/error_view.dart';
import '../../../core/widgets/loading_view.dart';
import '../../../core/widgets/primary_button.dart';
import '../../favorites/presentation/widgets/favorite_button.dart';
import '../domain/offer.dart';
import 'offer_providers.dart';

/// Backed by `GET /api/v1/offers/{offerId}`.
class OfferDetailScreen extends ConsumerWidget {
  const OfferDetailScreen({super.key, required this.offerId});

  final String offerId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final offerAsync = ref.watch(offerDetailProvider(offerId));

    return Scaffold(
      appBar: AppBar(
        title: const Text('Angebot'),
        actions: [FavoriteButton(offerId: offerId)],
      ),
      body: offerAsync.when(
        data: (offer) => _OfferDetailBody(offer: offer),
        loading: () => const LoadingView(),
        error: (error, stackTrace) => ErrorView(
          message: _errorMessage(error),
          onRetry: () => ref.invalidate(offerDetailProvider(offerId)),
        ),
      ),
    );
  }

  String _errorMessage(Object error) {
    if (error is AppException) return error.message;
    return 'Ein unerwarteter Fehler ist aufgetreten.';
  }
}

class _OfferDetailBody extends StatelessWidget {
  const _OfferDetailBody({required this.offer});

  final Offer offer;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (offer.images.isNotEmpty)
            ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: AspectRatio(
                aspectRatio: 4 / 3,
                child: Image.network(
                  offer.images.first,
                  fit: BoxFit.cover,
                  errorBuilder: (context, error, stackTrace) => ColoredBox(
                    color: Theme.of(context).colorScheme.surfaceContainerHighest,
                    child: const Icon(CupertinoIcons.photo),
                  ),
                ),
              ),
            ),
          const SizedBox(height: AppSpacing.md),
          Text(offer.title, style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: AppSpacing.sm),
          Text(
            '${offer.priceAmount.toStringAsFixed(2)} ${offer.priceCurrency}',
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  color: Theme.of(context).colorScheme.primary,
                  fontWeight: FontWeight.bold,
                ),
          ),
          if (offer.location != null) ...[
            const SizedBox(height: AppSpacing.xs),
            Row(
              children: [
                const Icon(CupertinoIcons.location, size: 18),
                const SizedBox(width: AppSpacing.xs),
                Text(offer.location!),
              ],
            ),
          ],
          const SizedBox(height: AppSpacing.lg),
          Text('Beschreibung', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: AppSpacing.sm),
          Text(offer.description),
          const SizedBox(height: AppSpacing.lg),
          PrimaryButton(
            label: 'Deal-Analyse ansehen',
            onPressed: () => context.push(RoutePaths.dealAnalysisPath(offer.id)),
          ),
          const SizedBox(height: AppSpacing.sm),
          PrimaryButton(
            label: 'Reparatur-Analyse ansehen',
            onPressed: () => context.push(RoutePaths.repairAnalysisPath(offer.id)),
          ),
          const SizedBox(height: AppSpacing.md),
          Align(
            alignment: Alignment.center,
            child: TextButton.icon(
              onPressed: () {
                // v1: no in-app browser/launcher dependency yet — showing
                // the source URL is the honest placeholder until Task #12's
                // follow-up wires url_launcher.
                // A native CupertinoAlertDialog here, not a themed Material
                // AlertDialog — iOS's own two-line-button alert proportions
                // (rounded top, centered text, hairline-divided actions)
                // aren't something a Material AlertDialog can be themed
                // into passably, unlike the app's other surfaces.
                showAppCupertinoDialog<void>(
                  context: context,
                  builder: (context) => CupertinoAlertDialog(
                    title: const Text('Original-Angebot'),
                    content: Padding(
                      padding: const EdgeInsets.only(top: AppSpacing.sm),
                      child: SelectableText(offer.url),
                    ),
                    actions: [
                      CupertinoDialogAction(
                        onPressed: () => Navigator.of(context).pop(),
                        child: const Text('Schließen'),
                      ),
                    ],
                  ),
                );
              },
              icon: const Icon(CupertinoIcons.arrow_up_right),
              label: const Text('Original-Angebot anzeigen'),
            ),
          ),
        ],
      ),
    );
  }
}
