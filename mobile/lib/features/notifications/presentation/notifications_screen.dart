import 'package:flutter/material.dart';

import '../../../core/widgets/empty_view.dart';

/// Placeholder — real UI (inbox + mark-as-read + preferences, backed by
/// `/api/v1/notifications*`) lands in Task #12.
class NotificationsScreen extends StatelessWidget {
  const NotificationsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Benachrichtigungen')),
      body: const EmptyView(
        icon: Icons.notifications_outlined,
        message: 'Deine Benachrichtigungen folgen in Task #12.',
      ),
    );
  }
}
