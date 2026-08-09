import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/error/app_exception.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/widgets/app_content_bounds.dart';
import '../../../core/widgets/app_cupertino_dialog.dart';
import '../../../core/widgets/empty_view.dart';
import '../../../core/widgets/error_view.dart';
import '../../../core/widgets/loading_view.dart';
import '../../offers/domain/offer_category.dart';
import '../domain/search_profile.dart';
import 'search_profiles_providers.dart';
import 'widgets/search_profile_form_sheet.dart';

/// Backed by `/api/v1/search-profiles` (full CRUD).
class SearchProfilesScreen extends ConsumerWidget {
  const SearchProfilesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final profilesAsync = ref.watch(searchProfilesControllerProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Gespeicherte Suchen')),
      floatingActionButton: FloatingActionButton(
        onPressed: () => showSearchProfileFormSheet(context),
        tooltip: 'Neue gespeicherte Suche',
        child: const Icon(CupertinoIcons.add),
      ),
      body: AppContentBounds(
        child: profilesAsync.when(
          data: (profiles) {
            if (profiles.isEmpty) {
              return const EmptyView(
                icon: CupertinoIcons.bookmark,
                message: 'Noch keine gespeicherten Suchen. Mit "+" eine neue anlegen.',
              );
            }
            return RefreshIndicator(
              onRefresh: () => ref.read(searchProfilesControllerProvider.notifier).refresh(),
              child: ListView.builder(
                padding:
                    const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: AppSpacing.sm),
                itemCount: profiles.length,
                itemBuilder: (context, index) => _SearchProfileCard(profile: profiles[index]),
              ),
            );
          },
          loading: () => const LoadingView(),
          error: (error, stackTrace) => ErrorView(
            message: _errorMessage(error),
            onRetry: () => ref.read(searchProfilesControllerProvider.notifier).refresh(),
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

class _SearchProfileCard extends ConsumerWidget {
  const _SearchProfileCard({required this.profile});

  final SearchProfile profile;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final categoryLabel = OfferCategory.fromApiValue(profile.category).label;
    final priceRange = _formatPriceRange(profile.minPrice, profile.maxPrice);

    return Card(
      margin: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: ListTile(
        onTap: () => showSearchProfileFormSheet(context, existing: profile),
        title: Text(profile.name),
        subtitle: Text(
          [
            categoryLabel,
            if (priceRange != null) priceRange,
            if (profile.keywords != null && profile.keywords!.isNotEmpty)
              '"${profile.keywords}"',
          ].join(' · '),
        ),
        trailing: IconButton(
          icon: const Icon(CupertinoIcons.trash),
          tooltip: 'Löschen',
          onPressed: () => _confirmDelete(context, ref),
        ),
      ),
    );
  }

  String? _formatPriceRange(double? min, double? max) {
    if (min == null && max == null) return null;
    if (min != null && max != null) {
      return '${min.toStringAsFixed(0)}–${max.toStringAsFixed(0)} €';
    }
    if (min != null) return 'ab ${min.toStringAsFixed(0)} €';
    return 'bis ${max!.toStringAsFixed(0)} €';
  }

  Future<void> _confirmDelete(BuildContext context, WidgetRef ref) async {
    final confirmed = await showAppCupertinoDialog<bool>(
      context: context,
      builder: (context) => CupertinoAlertDialog(
        title: const Text('Suche löschen?'),
        content: Text('"${profile.name}" wird endgültig gelöscht.'),
        actions: [
          CupertinoDialogAction(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Abbrechen'),
          ),
          CupertinoDialogAction(
            isDestructiveAction: true,
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Löschen'),
          ),
        ],
      ),
    );
    if (confirmed == true) {
      await ref.read(searchProfilesControllerProvider.notifier).delete(profile.id);
    }
  }
}
