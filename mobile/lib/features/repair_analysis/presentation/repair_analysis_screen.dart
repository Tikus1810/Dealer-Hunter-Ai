import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/error/app_exception.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/widgets/primary_button.dart';
import '../domain/repair_report.dart';
import 'repair_analysis_providers.dart';

/// Backed by `POST /api/v1/offers/{offerId}/repair-report` (RepairBrain).
/// The user lists any known defects (comma-separated) before triggering
/// the analysis — the backend distinguishes these "confirmed" facts from
/// its own text-based "inferred" guesses.
class RepairAnalysisScreen extends ConsumerStatefulWidget {
  const RepairAnalysisScreen({super.key, required this.offerId});

  final String offerId;

  @override
  ConsumerState<RepairAnalysisScreen> createState() => _RepairAnalysisScreenState();
}

class _RepairAnalysisScreenState extends ConsumerState<RepairAnalysisScreen> {
  final _defectsController = TextEditingController();

  @override
  void dispose() {
    _defectsController.dispose();
    super.dispose();
  }

  Future<void> _analyze() async {
    final defects = _defectsController.text
        .split(',')
        .map((defect) => defect.trim())
        .where((defect) => defect.isNotEmpty)
        .toList();
    await ref
        .read(repairAnalysisControllerProvider(widget.offerId).notifier)
        .analyze(reportedDefects: defects);
  }

  @override
  Widget build(BuildContext context) {
    final reportAsync = ref.watch(repairAnalysisControllerProvider(widget.offerId));

    return Scaffold(
      appBar: AppBar(title: const Text('Reparatur-Analyse')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            TextField(
              controller: _defectsController,
              decoration: const InputDecoration(
                labelText: 'Bekannte Mängel (durch Komma getrennt)',
                hintText: 'z. B. Akku schwach, Display-Kratzer',
              ),
              minLines: 1,
              maxLines: 3,
            ),
            const SizedBox(height: AppSpacing.md),
            PrimaryButton(
              label: 'Analysieren',
              isLoading: reportAsync.isLoading,
              onPressed: _analyze,
            ),
            const SizedBox(height: AppSpacing.lg),
            reportAsync.when(
              data: (report) =>
                  report == null ? const SizedBox.shrink() : _RepairReportBody(report: report),
              loading: () => const SizedBox.shrink(),
              error: (error, stackTrace) => Text(
                _errorMessage(error),
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
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

class _RepairReportBody extends StatelessWidget {
  const _RepairReportBody({required this.report});

  final RepairReport report;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Reparatur-Score', style: Theme.of(context).textTheme.bodyMedium),
                  Text(
                    '${report.repairScore}',
                    style: Theme.of(context).textTheme.headlineMedium,
                  ),
                ],
              ),
            ),
            Chip(label: Text(report.difficulty)),
          ],
        ),
        const SizedBox(height: AppSpacing.md),
        Text(report.summary),
        const SizedBox(height: AppSpacing.md),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(AppSpacing.md),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _StatRow(
                  label: 'Geschätzte Reparaturkosten',
                  value: '${report.estimatedRepairCost.toStringAsFixed(2)} €',
                ),
                _StatRow(
                  label: 'Geschätzte Reparaturzeit',
                  value: '${report.estimatedRepairTimeHours.toStringAsFixed(1)} Std.',
                ),
              ],
            ),
          ),
        ),
        if (report.requiredTools.isNotEmpty) ...[
          const SizedBox(height: AppSpacing.md),
          Text('Benötigte Werkzeuge', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: AppSpacing.sm),
          Wrap(
            spacing: AppSpacing.sm,
            runSpacing: AppSpacing.sm,
            children: [for (final tool in report.requiredTools) Chip(label: Text(tool))],
          ),
        ],
        if (report.compatibleParts.isNotEmpty) ...[
          const SizedBox(height: AppSpacing.md),
          Text('Ersatzteile', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: AppSpacing.sm),
          for (final part in report.compatibleParts)
            ListTile(
              contentPadding: EdgeInsets.zero,
              title: Text(part.name),
              subtitle: Text(part.availability),
              trailing: Text('${part.estimatedPrice.toStringAsFixed(2)} €'),
            ),
        ],
        if (report.riskNotes.isNotEmpty) ...[
          const SizedBox(height: AppSpacing.md),
          Text('Risikohinweise', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: AppSpacing.sm),
          for (final note in report.riskNotes)
            Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.xs),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(Icons.warning_amber_outlined, size: 18),
                  const SizedBox(width: AppSpacing.xs),
                  Expanded(child: Text(note)),
                ],
              ),
            ),
        ],
      ],
    );
  }
}

class _StatRow extends StatelessWidget {
  const _StatRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.xs),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label),
          Text(value, style: const TextStyle(fontWeight: FontWeight.bold)),
        ],
      ),
    );
  }
}
