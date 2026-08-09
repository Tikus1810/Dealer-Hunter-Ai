import 'dart:ui';

import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../layout/app_breakpoints.dart';
import '../theme/app_colors.dart';
import '../widgets/brand_mark.dart';
import '../widgets/tap_scale.dart';

/// Primary navigation scaffold (Band 04/redesign passes) — wraps the
/// app's 5 primary destinations in a `StatefulShellRoute.indexedStack` so
/// each tab keeps its own navigation stack and scroll position when you
/// switch away and back, instead of rebuilding from scratch every time.
///
/// **Adaptive, not just responsive**: below [AppBreakpoints.desktop] this
/// is the bottom "Liquid Nav" tab bar (a touch/phone idiom); at or above
/// it, it's a persistent left `NavigationRail` instead — a bottom tab bar
/// stretched across a 1280px Windows-exe window is exactly the "this is a
/// phone app, not a real program" tell the switch to the exe surfaced.
/// The two variants share the same `_destinations` list and selection
/// logic; only the chrome around them differs.
///
/// Detail/sub-pages (offer detail, deal/repair analysis, notifications)
/// stay as plain top-level routes outside this shell (see `app_router.dart`)
/// — they push full-screen over the tab bar, which is the more common
/// pattern for a "drill into one item" page than keeping tabs visible
/// underneath it.
class AppShell extends StatelessWidget {
  const AppShell({super.key, required this.navigationShell});

  final StatefulNavigationShell navigationShell;

  static const _destinations = [
    (icon: CupertinoIcons.house, selectedIcon: CupertinoIcons.house_fill, label: 'Start'),
    (icon: CupertinoIcons.tag, selectedIcon: CupertinoIcons.tag_fill, label: 'Angebote'),
    (icon: CupertinoIcons.bookmark, selectedIcon: CupertinoIcons.bookmark_fill, label: 'Suchen'),
    (icon: CupertinoIcons.heart, selectedIcon: CupertinoIcons.heart_fill, label: 'Favoriten'),
    (icon: CupertinoIcons.settings, selectedIcon: CupertinoIcons.settings_solid, label: 'Mehr'),
  ];

  void _onDestinationSelected(int index) => navigationShell.goBranch(
        index,
        // Tapping the already-selected tab pops it back to that branch's
        // own root instead of doing nothing — standard "tap Home again
        // to go home" behavior.
        initialLocation: index == navigationShell.currentIndex,
      );

  @override
  Widget build(BuildContext context) {
    final isDesktop = MediaQuery.sizeOf(context).width >= AppBreakpoints.desktop;

    if (isDesktop) {
      return Scaffold(
        body: Row(
          children: [
            _DesktopSideRail(
              selectedIndex: navigationShell.currentIndex,
              onDestinationSelected: _onDestinationSelected,
            ),
            const VerticalDivider(width: 1, color: Colors.white12),
            Expanded(child: navigationShell),
          ],
        ),
      );
    }

    return Scaffold(
      body: navigationShell,
      // Lets list content scroll *underneath* the tab bar instead of
      // stopping above it — required for the translucent-blur effect
      // below to actually show something moving behind the glass, the
      // way an iOS tab bar behaves over a scrolling list.
      extendBody: true,
      bottomNavigationBar: _LiquidNavBar(
        selectedIndex: navigationShell.currentIndex,
        onDestinationSelected: _onDestinationSelected,
      ),
    );
  }
}

/// The desktop-window navigation rail — a persistent, always-labeled left
/// sidebar (extended `NavigationRail`, not the icon-only compact variant)
/// with the brand mark at the top, the way a real Windows/macOS app's
/// sidebar reads (Mail, Slack, Spotify, ...), not a phone tab bar turned
/// sideways.
class _DesktopSideRail extends StatelessWidget {
  const _DesktopSideRail({required this.selectedIndex, required this.onDestinationSelected});

  final int selectedIndex;
  final ValueChanged<int> onDestinationSelected;

  static const _destinations = AppShell._destinations;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return Container(
      width: 240,
      color: AppColors.surfaceDark,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Padding(
            padding: EdgeInsets.fromLTRB(20, 24, 20, 16),
            child: Row(
              children: [
                BrandMark(size: 36),
                SizedBox(width: 10),
                Expanded(
                  child: Text(
                    'Deal Hunter AI',
                    style: TextStyle(fontWeight: FontWeight.w700, fontSize: 15),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
          ),
          const Divider(height: 1, color: Colors.white12),
          const SizedBox(height: 8),
          for (final (index, destination) in _destinations.indexed)
            _RailItem(
              icon: index == selectedIndex ? destination.selectedIcon : destination.icon,
              label: destination.label,
              selected: index == selectedIndex,
              color: colorScheme.primary,
              onTap: () => onDestinationSelected(index),
            ),
        ],
      ),
    );
  }
}

class _RailItem extends StatelessWidget {
  const _RailItem({
    required this.icon,
    required this.label,
    required this.selected,
    required this.color,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final bool selected;
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 3),
      child: TapScale(
        onTap: onTap,
        child: Container(
          height: 44,
          padding: const EdgeInsets.symmetric(horizontal: 12),
          decoration: BoxDecoration(
            color: selected ? color.withValues(alpha: 0.16) : Colors.transparent,
            borderRadius: BorderRadius.circular(10),
          ),
          child: Row(
            children: [
              Icon(icon, size: 20, color: selected ? color : Colors.white54),
              const SizedBox(width: 14),
              Text(
                label,
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: selected ? FontWeight.w600 : FontWeight.w400,
                  color: selected ? Colors.white : Colors.white70,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// "Liquid Navigation" tab bar: a frosted-glass bar with a glowing blue
/// pill that glides — not snaps — behind whichever tab is active,
/// approximating the fluid feel of Apple's newer "Liquid Glass"
/// navigation without needing custom fragment shaders (a real optical-
/// refraction effect was the fancier option offered and explicitly not
/// the one picked, on cost/risk grounds for a Chrome/web dev target).
class _LiquidNavBar extends StatelessWidget {
  const _LiquidNavBar({required this.selectedIndex, required this.onDestinationSelected});

  final int selectedIndex;
  final ValueChanged<int> onDestinationSelected;

  static const _destinations = AppShell._destinations;
  static const _barHeight = 64.0;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return ClipRect(
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 24, sigmaY: 24),
        // Frosted-glass tab bar: iOS tab/nav bars are translucent and
        // blur whatever scrolls behind them, not an opaque Material
        // surface — a thin top hairline instead of elevation/shadow.
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: AppColors.surfaceDark.withValues(alpha: 0.72),
            border: const Border(top: BorderSide(color: Colors.white12)),
          ),
          child: SafeArea(
            top: false,
            child: SizedBox(
              height: _barHeight,
              child: LayoutBuilder(
                builder: (context, constraints) {
                  final itemWidth = constraints.maxWidth / _destinations.length;
                  const pillMargin = 8.0;

                  return Stack(
                    children: [
                      // The pill itself: `AnimatedPositioned` — not a
                      // discrete jump between tabs — is what reads as
                      // "liquid" rather than "highlighted", plus a glow
                      // (BoxShadow) and a top-to-bottom gradient standing
                      // in for a real glass refraction highlight.
                      AnimatedPositioned(
                        duration: const Duration(milliseconds: 380),
                        curve: Curves.easeOutBack,
                        left: itemWidth * selectedIndex + pillMargin,
                        width: itemWidth - pillMargin * 2,
                        top: 8,
                        bottom: 8,
                        child: DecoratedBox(
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(20),
                            gradient: LinearGradient(
                              begin: Alignment.topCenter,
                              end: Alignment.bottomCenter,
                              colors: [
                                colorScheme.primary.withValues(alpha: 0.38),
                                colorScheme.primary.withValues(alpha: 0.16),
                              ],
                            ),
                            border: Border.all(
                              color: colorScheme.primary.withValues(alpha: 0.55),
                            ),
                            boxShadow: [
                              BoxShadow(
                                color: colorScheme.primary.withValues(alpha: 0.45),
                                blurRadius: 18,
                                spreadRadius: -2,
                              ),
                            ],
                          ),
                        ),
                      ),
                      Row(
                        children: [
                          for (final (index, destination) in _destinations.indexed)
                            SizedBox(
                              width: itemWidth,
                              child: TapScale(
                                onTap: () => onDestinationSelected(index),
                                child: _NavItem(
                                  icon: index == selectedIndex
                                      ? destination.selectedIcon
                                      : destination.icon,
                                  label: destination.label,
                                  selected: index == selectedIndex,
                                ),
                              ),
                            ),
                        ],
                      ),
                    ],
                  );
                },
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _NavItem extends StatelessWidget {
  const _NavItem({required this.icon, required this.label, required this.selected});

  final IconData icon;
  final String label;
  final bool selected;

  @override
  Widget build(BuildContext context) {
    // White on the lit pill for the active tab (same "white on blue"
    // pairing as everywhere else in the third design pass), a dim
    // neutral gray for inactive tabs so they recede behind the glass.
    final color = selected ? Colors.white : Colors.white54;

    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Icon(icon, color: color, size: 24),
        const SizedBox(height: 2),
        Text(
          label,
          style: TextStyle(
            fontSize: 11,
            fontWeight: selected ? FontWeight.w600 : FontWeight.w400,
            color: color,
          ),
        ),
      ],
    );
  }
}
