import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';

import '../../../../core/theme/app_spacing.dart';
import '../../../../core/widgets/tap_scale.dart';
import '../../domain/offer.dart';

/// One offer's list-row representation — used by the offer list and (via
/// import from the `favorites` feature) the favorites list, so both stay
/// visually identical.
class OfferCard extends StatelessWidget {
  const OfferCard({super.key, required this.offer, required this.onTap});

  final Offer offer;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final imageUrl = offer.images.isNotEmpty ? offer.images.first : null;

    return TapScale(
      onTap: onTap,
      child: Card(
        margin: const EdgeInsets.only(bottom: AppSpacing.sm),
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.sm),
          child: Row(
            children: [
              ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: SizedBox(
                  width: 72,
                  height: 72,
                  child: imageUrl == null
                      ? ColoredBox(
                          color: Theme.of(context).colorScheme.surfaceContainerHighest,
                          child: Icon(
                            CupertinoIcons.photo,
                            color: Theme.of(context).colorScheme.outline,
                          ),
                        )
                      : Image.network(
                          imageUrl,
                          fit: BoxFit.cover,
                          errorBuilder: (context, error, stackTrace) => ColoredBox(
                            color: Theme.of(context).colorScheme.surfaceContainerHighest,
                            child: Icon(
                              CupertinoIcons.photo,
                              color: Theme.of(context).colorScheme.outline,
                            ),
                          ),
                        ),
                ),
              ),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      offer.title,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.titleSmall,
                    ),
                    const SizedBox(height: AppSpacing.xs),
                    Text(
                      '${offer.priceAmount.toStringAsFixed(2)} ${offer.priceCurrency}',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            color: Theme.of(context).colorScheme.primary,
                            fontWeight: FontWeight.bold,
                          ),
                    ),
                    if (offer.location != null) ...[
                      const SizedBox(height: AppSpacing.xs),
                      Text(
                        offer.location!,
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ],
                ),
              ),
              Icon(
                CupertinoIcons.chevron_right,
                size: 18,
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
