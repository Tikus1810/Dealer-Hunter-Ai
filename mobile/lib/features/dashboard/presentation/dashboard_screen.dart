import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/router/route_paths.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/widgets/app_content_bounds.dart';
import '../../../core/widgets/tap_scale.dart';
import '../../auth/presentation/auth_providers.dart';
import '../../offers/domain/offer.dart';
import '../../offers/presentation/offer_providers.dart';

/// Home tab (Band 04: "Dashboard"). Restructured to follow a supplied
/// reference layout (header + shortcut chips + a highlight banner +
/// category grid + secondary-actions row), recolored to the app's own
/// Onyx/Candy-Blue palette rather than the reference's own colors.
///
/// Deliberately doesn't show fabricated stats ("3 new deals today!") —
/// there's no dashboard-summary endpoint on the backend yet to back that
/// with real numbers, and a plausible-looking fake number is worse than
/// no number (Band 16: AI Rules "explainable, honest" applies to the whole
/// product's tone, not just DealBrain's own output). Same reasoning is why
/// there's no user display name/avatar photo here: `AuthRepository`
/// exposes only "has a session or not", nothing about who — so the header
/// stays generic rather than inventing a name, and the highlight banner
/// below is labeled by the real category it's pulling from rather than
/// implied to be some smart "best deal" pick that doesn't exist yet.
class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  // One-off per-item accents intentionally *not* used here (unlike the
  // pre-rebrand version of this screen) — the "Onyx + Candy Blue" palette
  // direction is explicitly a two-color combination, so every tile below
  // reuses `colorScheme.primary` at different opacities instead of a
  // distinct hue per destination.
  static const _sections = [
    (
      label: 'Angebote',
      subtitle: 'Aktuelle Deals durchsuchen',
      icon: CupertinoIcons.tag,
      path: RoutePaths.offers,
    ),
    (
      label: 'Suchen',
      subtitle: 'Automatisch benachrichtigt werden',
      icon: CupertinoIcons.bookmark,
      path: RoutePaths.searchProfiles,
    ),
    (
      label: 'Favoriten',
      subtitle: 'Gemerkte Angebote ansehen',
      icon: CupertinoIcons.heart,
      path: RoutePaths.favorites,
    ),
    (
      label: 'Einstellungen',
      subtitle: 'Konto verwalten',
      icon: CupertinoIcons.settings,
      path: RoutePaths.settings,
    ),
  ];

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      body: SafeArea(
        child: AppContentBounds(
          maxWidth: 1100,
          child: ListView(
            padding: const EdgeInsets.fromLTRB(
              AppSpacing.md,
              AppSpacing.md,
              AppSpacing.md,
              AppSpacing.xl,
            ),
            children: [
              _DashboardHeader(
                onLogout: () => ref.read(authControllerProvider.notifier).logout(),
              ),
              const SizedBox(height: AppSpacing.lg),
              const _ShortcutChipRow(sections: _sections),
              const SizedBox(height: AppSpacing.lg),
              const _HighlightOfferBanner(),
              const SizedBox(height: AppSpacing.lg),
              Text('Kategorien', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: AppSpacing.sm),
              LayoutBuilder(
                builder: (context, constraints) {
                  // 2 columns on a phone-width column, more as the
                  // (already width-capped) content area grows — a fixed
                  // 2-column grid stretched across a wide desktop window
                  // was the single worst offender for "mobile layout
                  // just made wider" on this screen.
                  final columns = (constraints.maxWidth / 240).floor().clamp(2, 4);
                  return GridView.count(
                    crossAxisCount: columns,
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    mainAxisSpacing: AppSpacing.sm,
                    crossAxisSpacing: AppSpacing.sm,
                    childAspectRatio: 1.5,
                    children: [
                      for (final section in _sections) _CategoryTile(section: section),
                    ],
                  );
                },
              ),
              const SizedBox(height: AppSpacing.lg),
              Text('Weitere', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: AppSpacing.sm),
              Row(
                children: [
                  _CircleAction(
                    icon: CupertinoIcons.bell,
                    label: 'Mitteilungen',
                    onTap: () => context.push(RoutePaths.notifications),
                  ),
                  const SizedBox(width: AppSpacing.lg),
                  _CircleAction(
                    icon: CupertinoIcons.square_arrow_right,
                    label: 'Abmelden',
                    onTap: () => ref.read(authControllerProvider.notifier).logout(),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _DashboardHeader extends StatelessWidget {
  const _DashboardHeader({required this.onLogout});

  final VoidCallback onLogout;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return Row(
      children: [
        // A generic silhouette, not a fake photo/initials — there's no
        // profile data (name, avatar) available from the backend session
        // to show here honestly (see this file's docstring).
        Container(
          width: 48,
          height: 48,
          decoration: BoxDecoration(
            color: colorScheme.primary.withValues(alpha: 0.16),
            shape: BoxShape.circle,
          ),
          child: Icon(CupertinoIcons.person_fill, color: colorScheme.primary, size: 24),
        ),
        const SizedBox(width: AppSpacing.md),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Willkommen zurück', style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 2),
              Text(
                'Schau, was es Neues bei deinen Angeboten gibt.',
                style: Theme.of(
                  context,
                ).textTheme.bodySmall?.copyWith(color: colorScheme.onSurfaceVariant),
              ),
            ],
          ),
        ),
        TapScale(
          onTap: () => context.push(RoutePaths.notifications),
          child: Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: AppColors.surfaceDark,
              shape: BoxShape.circle,
              border: Border.all(color: Colors.white12),
            ),
            child: Icon(CupertinoIcons.bell, color: colorScheme.onSurface, size: 18),
          ),
        ),
      ],
    );
  }
}

class _ShortcutChipRow extends StatelessWidget {
  const _ShortcutChipRow({required this.sections});

  final List<({String label, String subtitle, IconData icon, String path})> sections;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return SizedBox(
      height: 36,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: sections.length,
        separatorBuilder: (context, index) => const SizedBox(width: AppSpacing.sm),
        itemBuilder: (context, index) {
          // The first chip stands in for "everything" (this screen
          // itself) and reads as the active filter — matching the
          // reference layout's highlighted first chip — the rest are
          // plain shortcuts, not real filters (nothing here changes what
          // the highlight banner or grid below shows).
          final isFirst = index == 0;
          final section = sections[index];
          return TapScale(
            onTap: () => context.go(section.path),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: isFirst ? colorScheme.primary : AppColors.surfaceDark,
                borderRadius: BorderRadius.circular(18),
                border: isFirst ? null : Border.all(color: Colors.white12),
              ),
              child: Text(
                section.label,
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: isFirst ? Colors.white : colorScheme.onSurfaceVariant,
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}

/// Real data, not a fabricated promo carousel: the first offer of
/// whichever category is currently selected app-wide (the same provider
/// the Offers tab itself reads — see `offer_providers.dart`), labeled by
/// that category so it's clear this is "an offer from X", not a claimed
/// smart pick (DealBrain's score isn't a sort key on this endpoint).
class _HighlightOfferBanner extends ConsumerWidget {
  const _HighlightOfferBanner();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final category = ref.watch(selectedOfferCategoryProvider);
    final offerPageAsync = ref.watch(offerListProvider);
    final colorScheme = Theme.of(context).colorScheme;

    return offerPageAsync.when(
      data: (page) {
        if (page.items.isEmpty) return const _HighlightFallbackBanner();
        return _HighlightOfferCard(offer: page.items.first, categoryLabel: category.label);
      },
      loading: () => Container(
        height: 140,
        decoration: BoxDecoration(
          color: AppColors.surfaceDark,
          borderRadius: BorderRadius.circular(20),
        ),
        alignment: Alignment.center,
        child: CupertinoActivityIndicator(color: colorScheme.onSurfaceVariant),
      ),
      // A failed fetch here shouldn't block the rest of the dashboard —
      // fall back to the generic branded banner instead of an ErrorView.
      error: (error, stackTrace) => const _HighlightFallbackBanner(),
    );
  }
}

class _HighlightOfferCard extends StatelessWidget {
  const _HighlightOfferCard({required this.offer, required this.categoryLabel});

  final Offer offer;
  final String categoryLabel;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return TapScale(
      onTap: () => context.go(RoutePaths.offerDetailPath(offer.id)),
      child: Container(
        padding: const EdgeInsets.all(AppSpacing.lg),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(20),
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [colorScheme.primary, const Color(0xFF063C7A)],
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              categoryLabel.toUpperCase(),
              style: const TextStyle(
                color: Colors.white70,
                fontSize: 11,
                fontWeight: FontWeight.w700,
                letterSpacing: 0.6,
              ),
            ),
            const SizedBox(height: AppSpacing.xs),
            Text(
              offer.title,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: AppSpacing.sm),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  '${offer.priceAmount.toStringAsFixed(2)} ${offer.priceCurrency}',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 20,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: 6),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        'Ansehen',
                        style: TextStyle(
                          color: colorScheme.primary,
                          fontWeight: FontWeight.w700,
                          fontSize: 13,
                        ),
                      ),
                      const SizedBox(width: 4),
                      Icon(CupertinoIcons.chevron_right, size: 14, color: colorScheme.primary),
                    ],
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

/// Shown while there's genuinely nothing to highlight yet (no offers
/// fetched for the current category, or the fetch failed) — a branded
/// welcome card instead of an empty gap or a fabricated number.
class _HighlightFallbackBanner extends StatelessWidget {
  const _HighlightFallbackBanner();

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return Container(
      padding: const EdgeInsets.all(AppSpacing.lg),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        color: AppColors.surfaceDark,
        border: Border.all(color: Colors.white12),
      ),
      child: Row(
        children: [
          Icon(CupertinoIcons.tag, color: colorScheme.primary, size: 28),
          const SizedBox(width: AppSpacing.md),
          Expanded(
            child: Text(
              'Noch keine Angebote geladen — schau in den Angeboten vorbei.',
              style: TextStyle(color: colorScheme.onSurfaceVariant),
            ),
          ),
        ],
      ),
    );
  }
}

class _CategoryTile extends StatelessWidget {
  const _CategoryTile({required this.section});

  final ({String label, String subtitle, IconData icon, String path}) section;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return TapScale(
      onTap: () => context.go(section.path),
      child: Container(
        padding: const EdgeInsets.all(AppSpacing.md),
        decoration: BoxDecoration(
          color: colorScheme.primary.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: colorScheme.primary.withValues(alpha: 0.25)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Icon(section.icon, color: colorScheme.primary, size: 26),
            Text(
              section.label,
              style: Theme.of(
                context,
              ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700),
            ),
          ],
        ),
      ),
    );
  }
}

class _CircleAction extends StatelessWidget {
  const _CircleAction({required this.icon, required this.label, required this.onTap});

  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return TapScale(
      onTap: onTap,
      child: Column(
        children: [
          Container(
            width: 56,
            height: 56,
            decoration: BoxDecoration(
              color: colorScheme.primary.withValues(alpha: 0.14),
              shape: BoxShape.circle,
            ),
            child: Icon(icon, color: colorScheme.primary, size: 24),
          ),
          const SizedBox(height: AppSpacing.xs),
          Text(label, style: Theme.of(context).textTheme.bodySmall),
        ],
      ),
    );
  }
}
