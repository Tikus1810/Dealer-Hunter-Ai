import 'package:flutter/material.dart';

import '../../../core/widgets/empty_view.dart';

/// Placeholder — real UI (backed by `GET /api/v1/offers/{offerId}`, plus
/// links into Deal/Repair Analysis and the favorite toggle) lands in
/// Task #12.
class OfferDetailScreen extends StatelessWidget {
  const OfferDetailScreen({super.key, required this.offerId});

  final String offerId;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Angebot')),
      body: EmptyView(
        icon: Icons.local_offer_outlined,
        message: 'Details für Angebot $offerId folgen in Task #12.',
      ),
    );
  }
}
