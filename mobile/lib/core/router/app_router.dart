import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/auth/presentation/auth_providers.dart';
import '../../features/auth/presentation/login_screen.dart';
import '../../features/auth/presentation/register_screen.dart';
import '../../features/dashboard/presentation/dashboard_screen.dart';
import '../../features/deal_analysis/presentation/deal_analysis_screen.dart';
import '../../features/favorites/presentation/favorites_screen.dart';
import '../../features/notifications/presentation/notifications_screen.dart';
import '../../features/offers/presentation/offer_detail_screen.dart';
import '../../features/offers/presentation/offer_list_screen.dart';
import '../../features/repair_analysis/presentation/repair_analysis_screen.dart';
import '../../features/search_profiles/presentation/search_profiles_screen.dart';
import '../../features/settings/presentation/settings_screen.dart';
import 'route_paths.dart';

/// Bridges Riverpod state changes into go_router's `Listenable`-based
/// refresh mechanism, so a login/logout immediately re-evaluates
/// `redirect` without needing a manual `context.go` call from the screen
/// that triggered it.
class _GoRouterRefreshNotifier extends ChangeNotifier {
  _GoRouterRefreshNotifier(Ref ref) {
    ref.listen<AsyncValue<bool>>(authControllerProvider, (_, __) => notifyListeners());
  }
}

/// Navigation (Band 04: go_router, deep-linking ready). Auth-gated via
/// `redirect`: every route except `/login` and `/register` requires
/// `authControllerProvider` to report an active session.
///
/// Only ever mounted once the initial session check has resolved — see
/// `app.dart`, which shows a loading splash instead of `MaterialApp.router`
/// while `authControllerProvider` is still loading, so `redirect` below
/// never has to account for an "unknown yet" auth state.
final appRouterProvider = Provider<GoRouter>((ref) {
  final refreshNotifier = _GoRouterRefreshNotifier(ref);
  ref.onDispose(refreshNotifier.dispose);

  return GoRouter(
    initialLocation: RoutePaths.dashboard,
    refreshListenable: refreshNotifier,
    redirect: (context, state) {
      final authState = ref.read(authControllerProvider);
      // .valueOrNull, not .value: in Riverpod 2.x, AsyncValue.value rethrows
      // the underlying error when the state is AsyncError — .valueOrNull is
      // the null-safe accessor (this got renamed to .value only in
      // Riverpod 3.x, which this app deliberately isn't on yet).
      final isLoggedIn = authState.valueOrNull ?? false;
      final isAuthRoute =
          state.matchedLocation == RoutePaths.login || state.matchedLocation == RoutePaths.register;

      if (!isLoggedIn && !isAuthRoute) return RoutePaths.login;
      if (isLoggedIn && isAuthRoute) return RoutePaths.dashboard;
      return null;
    },
    routes: [
      GoRoute(path: RoutePaths.login, builder: (context, state) => const LoginScreen()),
      GoRoute(path: RoutePaths.register, builder: (context, state) => const RegisterScreen()),
      GoRoute(path: RoutePaths.dashboard, builder: (context, state) => const DashboardScreen()),
      GoRoute(
        path: RoutePaths.searchProfiles,
        builder: (context, state) => const SearchProfilesScreen(),
      ),
      GoRoute(path: RoutePaths.offers, builder: (context, state) => const OfferListScreen()),
      GoRoute(
        path: RoutePaths.offerDetail,
        builder: (context, state) =>
            OfferDetailScreen(offerId: state.pathParameters['offerId']!),
      ),
      GoRoute(
        path: RoutePaths.dealAnalysis,
        builder: (context, state) =>
            DealAnalysisScreen(offerId: state.pathParameters['offerId']!),
      ),
      GoRoute(
        path: RoutePaths.repairAnalysis,
        builder: (context, state) =>
            RepairAnalysisScreen(offerId: state.pathParameters['offerId']!),
      ),
      GoRoute(path: RoutePaths.favorites, builder: (context, state) => const FavoritesScreen()),
      GoRoute(
        path: RoutePaths.notifications,
        builder: (context, state) => const NotificationsScreen(),
      ),
      GoRoute(path: RoutePaths.settings, builder: (context, state) => const SettingsScreen()),
    ],
  );
});
