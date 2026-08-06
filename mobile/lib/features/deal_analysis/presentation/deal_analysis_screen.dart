import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/error/app_exception.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/widgets/error_view.dart';
import '../../../core/widgets/loading_view.dart';
import '../domain/deal_score.dart';
import 'deal_score_providers.dart';

/// Backed by `GET /api/v1/offers/{offerId}/deal-score` (DealBrain).
class DealAnalysisScreen extends ConsumerWidget {
  const DealAnalysisScreen({super.key, required this.offerId});

  final String offerId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dealScoreAsync = ref.watch(dealScoreProvider(offerId));

    return Scaffold(
      appBar: AppBar(title: const Text('Deal-Analyse')),
      body: dealScoreAsync.when(
        data: (dealScore) => _DealScoreBody(dealScore: dealScore),
        loading: () => const LoadingView(),
        error: (error, stackTrace) => ErrorView(
          message: _errorMessage(error),
          onRetry: () => ref.invalidate(dealScoreProvider(offerId)),
        ),
      ),
    );
  }

  String _errorMessage(Object error) {
    if (error is AppException) return error.message;
    return 'Ein unerwarteter Fehler ist aufgetreten.';
  }
}

class _DealScoreBody extends StatelessWidget {
  const _DealScoreBody({required this.dealScore});

  final DealScore dealScore;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Center(
            child: Column(
              children: [
                Text(
                  '${dealScore.score}',
                  style: Theme.of(context).textTheme.displayMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                        color: _scoreColor(colorScheme, dealScore.score),
                      ),
                ),
                Text('von 100 Punkten', style: Theme.of(context).textTheme.bodyMedium),
                const SizedBox(height: AppSpacing.sm),
                Chip(label: Text(dealScore.recommendation)),
              ],
            ),
          ),
          const SizedBox(height: AppSpacing.lg),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(AppSpacing.md),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _StatRow(
                    label: 'Geschätzter Marktwert',
                    value: '${dealScore.estimatedMarketValue.toStringAsFixed(2)} €',
                  ),
                  _StatRow(
                    label: 'Geschätzte Gesamtkosten',
                    value: '${dealScore.estimatedTotalCost.toStringAsFixed(2)} €',
                  ),
                  _StatRow(
                    label: 'Konfidenz',
                    value: '${(dealScore.confidence * 100).toStringAsFixed(0)} %',
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: AppSpacing.lg),
          Text('Begründung', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: AppSpacing.sm),
          for (final factor in dealScore.explanation) _ExplanationTile(factor: factor),
          const SizedBox(height: AppSpacing.lg),
          Center(
            child: Text(
              'Scoring-Version ${dealScore.scoringVersion}',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ),
        ],
      ),
    );
  }

  Color _scoreColor(ColorScheme colorScheme, int score) {
    if (score >= 70) return Colors.green.shade700;
    if (score >= 40) return Colors.orange.shade800;
    return colorScheme.error;
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

class _ExplanationTile extends StatelessWidget {
  const _ExplanationTile({required this.factor});

  final ExplanationFactor factor;

  @override
  Widget build(BuildContext context) {
    final isPositive = factor.impact >= 0;
    final color = isPositive ? Colors.green.shade700 : Theme.of(context).colorScheme.error;

    return Card(
      margin: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: ListTile(
        leading: Icon(
          isPositive ? Icons.arrow_upward : Icons.arrow_downward,
          color: color,
        ),
        title: Text(_humanizeFactorName(factor.name)),
        subtitle: Text(factor.description),
        trailing: Text(
          factor.impact.toStringAsFixed(1),
          style: TextStyle(color: color, fontWeight: FontWeight.bold),
        ),
      ),
    );
  }

  String _humanizeFactorName(String name) => name.replaceAll('_', ' ');
}
