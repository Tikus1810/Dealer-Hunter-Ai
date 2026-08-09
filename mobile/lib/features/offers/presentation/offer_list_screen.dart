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
import '../domain/offer.dart';
import '../domain/offer_category.dart';
import 'offer_providers.dart';
import 'widgets/offer_card.dart';

/// Backed by `GET /api/v1/offers?category=&page=&page_size=`.
class OfferListScreen extends ConsumerWidget {
  const OfferListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final selectedCategory = ref.watch(selectedOfferCategoryProvider);
    final offerPageAsync = ref.watch(offerListProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Angebote')),
      body: AppContentBounds(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(
                AppSpacing.md,
                AppSpacing.md,
                AppSpacing.md,
                AppSpacing.sm,
              ),
              child: DropdownButtonFormField<OfferCategory>(
                value: selectedCategory,
                // Not a change to the deprecated `value:`/`initialValue:`
                // param itself (see CLAUDE.md — CI still pins a Flutter
                // version without `initialValue:`), just the dropdown's own
                // caret glyph so it doesn't stand out as the one obviously
                // Material-styled control on the page.
                icon: const Icon(CupertinoIcons.chevron_down, size: 18),
                decoration: const InputDecoration(labelText: 'Kategorie'),
                items: [
                  for (final category in OfferCategory.values)
                    DropdownMenuItem(value: category, child: Text(category.label)),
                ],
                onChanged: (category) {
                  if (category == null) return;
                  ref.read(selectedOfferCategoryProvider.notifier).state = category;
                  ref.read(offerListPageProvider.notifier).state = 1;
                },
              ),
            ),
            Expanded(
              child: offerPageAsync.when(
                data: (page) => _OfferListBody(page: page),
                loading: () => const LoadingView(),
                error: (error, stackTrace) => ErrorView(
                  message: _errorMessage(error),
                  onRetry: () => ref.invalidate(offerListProvider),
                ),
              ),
            ),
            Consumer(
              builder: (context, ref, _) {
                final page = ref.watch(offerListProvider).valueOrNull;
                if (page == null) return const SizedBox.shrink();
                return _PaginationBar(page: page);
              },
            ),
          ],
        ),
      ),
    );
  }

  String _errorMessage(Object error) {
    if (error is AppException) return error.message;
    return 'Ein unerwarteter Fehler ist aufgetreten.';
  }
}

class _OfferListBody extends ConsumerWidget {
  const _OfferListBody({required this.page});

  final OfferPage page;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (page.items.isEmpty) {
      return const EmptyView(
        icon: CupertinoIcons.tag,
        message: 'Keine Angebote in dieser Kategorie gefunden.',
      );
    }
    return RefreshIndicator(
      onRefresh: () => ref.refresh(offerListProvider.future),
      child: ListView.builder(
        padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
        itemCount: page.items.length,
        itemBuilder: (context, index) {
          final offer = page.items[index];
          return OfferCard(
            offer: offer,
            onTap: () => context.push(RoutePaths.offerDetailPath(offer.id)),
          );
        },
      ),
    );
  }
}

class _PaginationBar extends ConsumerWidget {
  const _PaginationBar({required this.page});

  final OfferPage page;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: AppSpacing.sm),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          TextButton.icon(
            onPressed: page.hasPreviousPage
                ? () => ref.read(offerListPageProvider.notifier).state--
                : null,
            icon: const Icon(CupertinoIcons.chevron_left),
            label: const Text('Zurück'),
          ),
          Text('Seite ${page.page}'),
          TextButton.icon(
            onPressed:
                page.hasNextPage ? () => ref.read(offerListPageProvider.notifier).state++ : null,
            icon: const Icon(CupertinoIcons.chevron_right),
            label: const Text('Weiter'),
          ),
        ],
      ),
    );
  }
}
