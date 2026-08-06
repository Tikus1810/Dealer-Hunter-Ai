import 'package:flutter/material.dart';

import '../../../core/widgets/empty_view.dart';

/// Placeholder — real UI (paginated list backed by
/// `GET /api/v1/offers?category=&page=&page_size=`) lands in Task #12.
class OfferListScreen extends StatelessWidget {
  const OfferListScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Angebote')),
      body: const EmptyView(
        icon: Icons.local_offer_outlined,
        message: 'Die Angebotsliste folgt in Task #12.',
      ),
    );
  }
}
