import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/router/app_router.dart';
import 'core/theme/app_theme.dart';
import 'core/widgets/loading_view.dart';
import 'features/auth/presentation/auth_providers.dart';

class DealHunterApp extends ConsumerWidget {
  const DealHunterApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Gate the router entirely behind the initial session check — avoids
    // ever flashing the dashboard (or a redirect away from it) before we
    // actually know whether the stored tokens are still there.
    final isRestoringSession = ref.watch(authControllerProvider).isLoading;
    if (isRestoringSession) {
      return MaterialApp(
        title: 'Deal Hunter AI',
        debugShowCheckedModeBanner: false,
        theme: AppTheme.light,
        darkTheme: AppTheme.dark,
        themeMode: ThemeMode.system,
        home: const Scaffold(body: LoadingView()),
      );
    }

    final router = ref.watch(appRouterProvider);
    return MaterialApp.router(
      title: 'Deal Hunter AI',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      darkTheme: AppTheme.dark,
      themeMode: ThemeMode.system,
      routerConfig: router,
    );
  }
}
