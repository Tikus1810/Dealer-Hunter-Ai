import 'package:flutter/material.dart';

import '../../../core/widgets/empty_view.dart';

/// Placeholder — real UI (backed by `GET /api/v1/favorites`) lands in
/// Task #12.
class FavoritesScreen extends StatelessWidget {
  const FavoritesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Favoriten')),
      body: const EmptyView(
        icon: Icons.favorite_border,
        message: 'Deine Favoriten folgen in Task #12.',
      ),
    );
  }
}
