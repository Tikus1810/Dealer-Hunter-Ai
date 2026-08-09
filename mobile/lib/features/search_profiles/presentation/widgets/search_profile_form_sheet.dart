import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/error/app_exception.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/widgets/app_text_field.dart';
import '../../../../core/widgets/primary_button.dart';
import '../../../offers/domain/offer_category.dart';
import '../../domain/search_profile.dart';
import '../search_profiles_providers.dart';

/// Shows the create/edit form for a `SearchProfile` as a modal bottom
/// sheet. Pass `existing` to edit, or omit it to create a new profile.
Future<void> showSearchProfileFormSheet(BuildContext context, {SearchProfile? existing}) {
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    builder: (context) => _SearchProfileFormSheet(existing: existing),
  );
}

class _SearchProfileFormSheet extends ConsumerStatefulWidget {
  const _SearchProfileFormSheet({this.existing});

  final SearchProfile? existing;

  @override
  ConsumerState<_SearchProfileFormSheet> createState() => _SearchProfileFormSheetState();
}

class _SearchProfileFormSheetState extends ConsumerState<_SearchProfileFormSheet> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _nameController;
  late final TextEditingController _keywordsController;
  late final TextEditingController _minPriceController;
  late final TextEditingController _maxPriceController;
  late final TextEditingController _minDealScoreController;
  late OfferCategory _category;
  late bool _notifyOnMatch;
  bool _isSaving = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    final existing = widget.existing;
    _nameController = TextEditingController(text: existing?.name ?? '');
    _keywordsController = TextEditingController(text: existing?.keywords ?? '');
    _minPriceController = TextEditingController(text: existing?.minPrice?.toStringAsFixed(0) ?? '');
    _maxPriceController = TextEditingController(text: existing?.maxPrice?.toStringAsFixed(0) ?? '');
    _minDealScoreController = TextEditingController(
      text: existing?.minDealScore?.toString() ?? '',
    );
    _category = existing == null
        ? OfferCategory.macbook
        : OfferCategory.fromApiValue(existing.category);
    _notifyOnMatch = existing?.notifyOnMatch ?? true;
  }

  @override
  void dispose() {
    _nameController.dispose();
    _keywordsController.dispose();
    _minPriceController.dispose();
    _maxPriceController.dispose();
    _minDealScoreController.dispose();
    super.dispose();
  }

  double? _parseDouble(String text) => text.trim().isEmpty ? null : double.tryParse(text.trim());

  int? _parseInt(String text) => text.trim().isEmpty ? null : int.tryParse(text.trim());

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _isSaving = true;
      _errorMessage = null;
    });

    final controller = ref.read(searchProfilesControllerProvider.notifier);
    try {
      final existing = widget.existing;
      if (existing == null) {
        await controller.create(
          name: _nameController.text.trim(),
          category: _category.apiValue,
          keywords: _keywordsController.text.trim().isEmpty ? null : _keywordsController.text.trim(),
          minPrice: _parseDouble(_minPriceController.text),
          maxPrice: _parseDouble(_maxPriceController.text),
          minDealScore: _parseInt(_minDealScoreController.text),
          notifyOnMatch: _notifyOnMatch,
        );
      } else {
        await controller.update(
          existing.id,
          name: _nameController.text.trim(),
          category: _category.apiValue,
          keywords: _keywordsController.text.trim().isEmpty ? null : _keywordsController.text.trim(),
          minPrice: _parseDouble(_minPriceController.text),
          maxPrice: _parseDouble(_maxPriceController.text),
          minDealScore: _parseInt(_minDealScoreController.text),
          notifyOnMatch: _notifyOnMatch,
        );
      }
      if (!mounted) return;
      Navigator.of(context).pop();
    } on AppException catch (e) {
      setState(() => _errorMessage = e.message);
    } finally {
      if (mounted) setState(() => _isSaving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final isEditing = widget.existing != null;
    return Padding(
      padding: EdgeInsets.only(
        left: AppSpacing.lg,
        right: AppSpacing.lg,
        top: AppSpacing.lg,
        bottom: MediaQuery.of(context).viewInsets.bottom + AppSpacing.lg,
      ),
      child: SingleChildScrollView(
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                isEditing ? 'Suche bearbeiten' : 'Neue gespeicherte Suche',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: AppSpacing.md),
              AppTextField(
                controller: _nameController,
                label: 'Name',
                validator: (value) =>
                    (value == null || value.trim().isEmpty) ? 'Bitte einen Namen eingeben.' : null,
              ),
              const SizedBox(height: AppSpacing.md),
              DropdownButtonFormField<OfferCategory>(
                value: _category,
                icon: const Icon(CupertinoIcons.chevron_down, size: 18),
                decoration: const InputDecoration(labelText: 'Kategorie'),
                items: [
                  for (final category in OfferCategory.values)
                    DropdownMenuItem(value: category, child: Text(category.label)),
                ],
                onChanged: (category) {
                  if (category != null) setState(() => _category = category);
                },
              ),
              const SizedBox(height: AppSpacing.md),
              AppTextField(controller: _keywordsController, label: 'Stichwörter (optional)'),
              const SizedBox(height: AppSpacing.md),
              Row(
                children: [
                  Expanded(
                    child: AppTextField(
                      controller: _minPriceController,
                      label: 'Min. Preis (€)',
                      keyboardType: TextInputType.number,
                    ),
                  ),
                  const SizedBox(width: AppSpacing.md),
                  Expanded(
                    child: AppTextField(
                      controller: _maxPriceController,
                      label: 'Max. Preis (€)',
                      keyboardType: TextInputType.number,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: AppSpacing.md),
              AppTextField(
                controller: _minDealScoreController,
                label: 'Mindest-Deal-Score (0-100, optional)',
                keyboardType: TextInputType.number,
              ),
              const SizedBox(height: AppSpacing.sm),
              SwitchListTile.adaptive(
                contentPadding: EdgeInsets.zero,
                title: const Text('Bei Treffern benachrichtigen'),
                // `Switch.adaptive`'s iOS branch defaults to
                // `CupertinoColors.systemGreen`, not this app's brand
                // color — set explicitly so the one Cupertino-native
                // control on the page still reads as on-brand.
                //
                // `activeColor` itself (not `activeThumbColor`/
                // `activeTrackColor`) deliberately, same reasoning as the
                // `value:`/`initialValue:` DropdownButtonFormField note
                // below: CI still pins a Flutter version from before this
                // param split existed.
                activeColor: AppColors.seed,
                value: _notifyOnMatch,
                onChanged: (value) => setState(() => _notifyOnMatch = value),
              ),
              if (_errorMessage != null) ...[
                const SizedBox(height: AppSpacing.sm),
                Text(
                  _errorMessage!,
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                ),
              ],
              const SizedBox(height: AppSpacing.md),
              PrimaryButton(
                label: isEditing ? 'Speichern' : 'Erstellen',
                isLoading: _isSaving,
                onPressed: _save,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
