import 'package:flutter/material.dart';

import '../../../core/widgets/empty_view.dart';

/// Placeholder — real UI (list/create/edit saved searches, backed by
/// `GET/POST/PATCH/DELETE /api/v1/search-profiles`) lands in Task #12.
class SearchProfilesScreen extends StatelessWidget {
  const SearchProfilesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Gespeicherte Suchen')),
      body: const EmptyView(
        icon: Icons.saved_search_outlined,
        message: 'Gespeicherte Suchen folgen in Task #12.',
      ),
    );
  }
}
