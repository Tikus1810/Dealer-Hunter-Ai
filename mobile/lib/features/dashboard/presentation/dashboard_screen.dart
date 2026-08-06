import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/router/route_paths.dart';
import '../../../core/theme/app_spacing.dart';
import '../../auth/presentation/auth_providers.dart';

/// Home screen (Band 04: "Dashboard"). A navigation grid stands in for the
/// real dashboard content (recent deals, saved-search highlights, etc.) —
/// that content is Task #12's job; this foundation build just needs every
/// Band 04 "Core Feature" to be reachable.
class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  static const _destinations = [
    (label: 'Angebote', icon: Icons.local_offer_outlined, path: RoutePaths.offers),
    (label: 'Gespeicherte Suchen', icon: Icons.saved_search_outlined, path: RoutePaths.searchProfiles),
    (label: 'Favoriten', icon: Icons.favorite_border, path: RoutePaths.favorites),
    (label: 'Benachrichtigungen', icon: Icons.notifications_outlined, path: RoutePaths.notifications),
    (label: 'Einstellungen', icon: Icons.settings_outlined, path: RoutePaths.settings),
  ];

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Deal Hunter AI'),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: 'Abmelden',
            onPressed: () => ref.read(authControllerProvider.notifier).logout(),
          ),
        ],
      ),
      body: GridView.count(
        padding: const EdgeInsets.all(AppSpacing.md),
        crossAxisCount: 2,
        crossAxisSpacing: AppSpacing.md,
        mainAxisSpacing: AppSpacing.md,
        children: [
          for (final destination in _destinations)
            _DashboardTile(
              label: destination.label,
              icon: destination.icon,
              onTap: () => context.go(destination.path),
            ),
        ],
      ),
    );
  }
}

class _DashboardTile extends StatelessWidget {
  const _DashboardTile({required this.label, required this.icon, required this.onTap});

  final String label;
  final IconData icon;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 32),
            const SizedBox(height: AppSpacing.sm),
            Text(label, textAlign: TextAlign.center),
          ],
        ),
      ),
    );
  }
}
