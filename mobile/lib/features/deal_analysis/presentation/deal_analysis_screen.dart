import 'package:flutter/material.dart';

import '../../../core/widgets/empty_view.dart';

/// Placeholder — real UI (DealBrain score + explanation factors, backed by
/// `GET /api/v1/offers/{offerId}/deal-score`) lands in Task #12.
class DealAnalysisScreen extends StatelessWidget {
  const DealAnalysisScreen({super.key, required this.offerId});

  final String offerId;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Deal-Analyse')),
      body: EmptyView(
        icon: Icons.query_stats_outlined,
        message: 'Die Deal-Analyse für Angebot $offerId folgt in Task #12.',
      ),
    );
  }
}
