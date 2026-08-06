import 'package:flutter/material.dart';

import '../../../core/widgets/empty_view.dart';

/// Placeholder — real UI (RepairBrain report: cost, difficulty, parts,
/// backed by `POST /api/v1/offers/{offerId}/repair-report`) lands in
/// Task #12.
class RepairAnalysisScreen extends StatelessWidget {
  const RepairAnalysisScreen({super.key, required this.offerId});

  final String offerId;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Reparatur-Analyse')),
      body: EmptyView(
        icon: Icons.build_outlined,
        message: 'Die Reparatur-Analyse für Angebot $offerId folgt in Task #12.',
      ),
    );
  }
}
