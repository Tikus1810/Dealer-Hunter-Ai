import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/widgets/tap_scale.dart';
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
          TapScale(
            onTap: () => showNotificationPreferencesSheet(context),
            child: const ListTile(
              leading: Icon(CupertinoIcons.bell),
              title: Text('Benachrichtigungen'),
              subtitle: Text('Push und E-Mail pro Ereignis ein-/ausschalten'),
              trailing: Icon(CupertinoIcons.chevron_right, size: 18),
            ),
          ),
          const Divider(height: 1),
          TapScale(
            onTap: () => ref.read(authControllerProvider.notifier).logout(),
            child: const ListTile(
              leading: Icon(CupertinoIcons.square_arrow_right),
              title: Text('Abmelden'),
            ),
          ),
        ],
      ),
    );
  }
}
