import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../auth/presentation/auth_providers.dart';
import '../../notifications/presentation/widgets/notification_preferences_sheet.dart';

/// Real content: notification preferences + logout. Profile editing isn't
/// backed by anything yet (no `PATCH /users/me` field beyond
/// `display_name`, and no UI for it was in this task's scope) — flagged
/// here rather than silently missing.
class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      appBar: AppBar(title: const Text('Einstellungen')),
      body: ListView(
        children: [
          ListTile(
            leading: const Icon(Icons.notifications_outlined),
            title: const Text('Benachrichtigungen'),
            subtitle: const Text('Push und E-Mail pro Ereignis ein-/ausschalten'),
            onTap: () => showNotificationPreferencesSheet(context),
          ),
          const Divider(height: 1),
          ListTile(
            leading: const Icon(Icons.logout),
            title: const Text('Abmelden'),
            onTap: () => ref.read(authControllerProvider.notifier).logout(),
          ),
        ],
      ),
    );
  }
}
