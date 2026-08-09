import 'package:flutter/cupertino.dart' show CupertinoPageTransitionsBuilder;
import 'package:flutter/material.dart';

import 'app_colors.dart';
import 'app_spacing.dart';
import 'app_typography.dart';

/// Material 3 theme (Band 04 / redesign passes).
///
/// **Second redesign pass**: black background + accent-colored text,
/// explicitly less "Material/Android-coded" — flat surfaces (no card
/// shadows, thin hairline borders instead), no ripple/splash touch
/// feedback, iOS-style flat nav/app bars. `light` and `dark` now render
/// the *same* look rather than a conventional pair: this is a fixed
/// brand identity, not a system-theme-following one — a deliberate
/// choice given explicitly, not a leftover Material default. Still built
/// from token files here (`AppColors`), so a future direction change is
/// still a small, localized edit, not an app-wide find/replace.
///
/// **Third pass ("Onyx + Candy Blue")**: same architecture, `AppColors
/// .seed` recolored from gold to blue and `AppColors.surfaceDark` warmed
/// up — see that file's docstrings. `onPrimary` flips from black to
/// white here specifically because of that recolor: black-on-yellow was
/// the highest-contrast pairing for a light, saturated accent; white is
/// the equivalent pairing now that the accent (`#0A84FF`) is a mid-tone
/// blue instead — Apple's own systemBlue-filled buttons use white
/// labels for the same reason.
class AppTheme {
  const AppTheme._();

  static ThemeData get light => _theme();

  static ThemeData get dark => _theme();

  static ThemeData _theme() {
    final baseScheme = ColorScheme.fromSeed(
      seedColor: AppColors.seed,
      brightness: Brightness.dark,
    );
    // `.fromSeed` alone gives a dark-toned surface with a slight seed-hue
    // cast (Material 3's usual tonal-palette approach), not the literal
    // pure black that was asked for — overridden explicitly below, same
    // for making body text itself accent-colored (not just accents) and
    // giving primary-colored surfaces the highest-contrast text pairing
    // for whatever `AppColors.seed` currently is.
    final colorScheme = baseScheme.copyWith(
      surface: AppColors.backgroundBlack,
      onSurface: AppColors.seed,
      onSurfaceVariant: AppColors.seed.withValues(alpha: 0.7),
      primary: AppColors.seed,
      onPrimary: Colors.white,
      surfaceContainerLow: AppColors.surfaceDark,
      surfaceContainerHighest: AppColors.surfaceDark,
      outline: Colors.white24,
      outlineVariant: Colors.white12,
    );
    final baseTextTheme = ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      colorScheme: colorScheme,
    ).textTheme;

    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      colorScheme: colorScheme,
      // Forces every `.adaptive()` widget (Switch, CircularProgressIndicator,
      // Slider, AlertDialog.adaptive, ...) to resolve to its Cupertino-styled
      // branch regardless of the actual host OS — this app runs on Windows/
      // web dev targets today, which would otherwise make `.adaptive()`
      // widgets render as plain Material even though the whole rest of the
      // theme is iOS-styled. Also switches the default scroll physics to
      // `BouncingScrollPhysics` (iOS's overscroll bounce) instead of
      // Material's clamping behavior — another small but real "feels like
      // an iPhone" cue, for free, app-wide.
      platform: TargetPlatform.iOS,
      fontFamily: AppTypography.fontFamily,
      textTheme: AppTypography.apply(baseTextTheme).apply(
            bodyColor: colorScheme.onSurface,
            displayColor: colorScheme.onSurface,
          ),
      scaffoldBackgroundColor: AppColors.backgroundBlack,
      // No ripple/highlight splash on tap — the single most "this is a
      // Material/Android app" tell on any button or list tile, and the
      // one asked to go specifically.
      splashFactory: NoSplash.splashFactory,
      splashColor: Colors.transparent,
      highlightColor: Colors.transparent,
      // Every push/pop on every platform (including the Windows/web dev
      // targets this app actually runs on) uses iOS's own slide-in-from-
      // the-right transition + interactive edge-swipe-back, instead of
      // Material's fade-through/vertical-lift default — one of the most
      // immediately recognizable "this feels like an iPhone app" cues,
      // and it's a single theme-level switch rather than a per-screen one.
      pageTransitionsTheme: const PageTransitionsTheme(
        builders: {
          TargetPlatform.android: CupertinoPageTransitionsBuilder(),
          TargetPlatform.iOS: CupertinoPageTransitionsBuilder(),
          TargetPlatform.windows: CupertinoPageTransitionsBuilder(),
          TargetPlatform.macOS: CupertinoPageTransitionsBuilder(),
          TargetPlatform.linux: CupertinoPageTransitionsBuilder(),
          TargetPlatform.fuchsia: CupertinoPageTransitionsBuilder(),
        },
      ),
      appBarTheme: AppBarTheme(
        backgroundColor: AppColors.backgroundBlack,
        foregroundColor: colorScheme.onSurface,
        elevation: 0,
        // Left-aligned, not centered: iOS's large-title navigation bar
        // (HIG default since iOS 11) sets the title flush with the
        // leading edge, not centered the way Material app bars are.
        centerTitle: false,
        titleTextStyle: AppTypography.apply(baseTextTheme).titleLarge?.copyWith(
              color: colorScheme.onSurface,
              fontWeight: FontWeight.w700,
            ),
      ),
      // Rounded, centered iOS-alert proportions (14px corner radius,
      // matches CupertinoAlertDialog's own) for any `showDialog` call
      // site that still builds a Material `AlertDialog` rather than a
      // `CupertinoAlertDialog` directly.
      dialogTheme: DialogThemeData(
        backgroundColor: AppColors.surfaceDark,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(14),
          side: const BorderSide(color: Colors.white12),
        ),
      ),
      // Floating, rounded, dark — closer to an iOS toast/banner than
      // Material's default full-width bar glued to the bottom edge.
      snackBarTheme: SnackBarThemeData(
        backgroundColor: AppColors.surfaceDark,
        contentTextStyle: TextStyle(color: colorScheme.onSurface),
        behavior: SnackBarBehavior.floating,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: const BorderSide(color: Colors.white12),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: colorScheme.primary,
          foregroundColor: colorScheme.onPrimary,
          disabledBackgroundColor: Colors.white24,
          disabledForegroundColor: Colors.white38,
          // Flat, no shadow — iOS buttons don't float above the page the
          // way Material's default elevation implies.
          elevation: 0,
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg, vertical: AppSpacing.md),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(28)),
          textStyle: const TextStyle(fontWeight: FontWeight.w600),
        ).copyWith(splashFactory: NoSplash.splashFactory),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: colorScheme.primary,
          side: BorderSide(color: colorScheme.primary),
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg, vertical: AppSpacing.md),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(28)),
        ).copyWith(splashFactory: NoSplash.splashFactory),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: AppColors.surfaceDark,
        labelStyle: TextStyle(color: colorScheme.onSurfaceVariant),
        hintStyle: TextStyle(color: colorScheme.onSurfaceVariant),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: Colors.white12),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: Colors.white12),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: colorScheme.primary, width: 2),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: AppSpacing.md),
      ),
      // Flat card, hairline border instead of a drop shadow — Material's
      // elevation/shadow model is exactly the "Android-coded" look this
      // pass moves away from; iOS's own grouped-list surfaces separate
      // from the page with a border/tone change, not a shadow.
      cardTheme: CardThemeData(
        elevation: 0,
        color: AppColors.surfaceDark,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: const BorderSide(color: Colors.white12),
        ),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: AppColors.surfaceDark,
        labelStyle: TextStyle(color: colorScheme.onSurfaceVariant),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
          side: const BorderSide(color: Colors.white12),
        ),
      ),
      // Rounded top corners, no square Material sheet edge — every
      // `showModalBottomSheet` call in the app (search-profile form,
      // notification preferences) picks this up automatically without
      // needing its own `shape:` override.
      bottomSheetTheme: const BottomSheetThemeData(
        backgroundColor: AppColors.surfaceDark,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        showDragHandle: true,
        dragHandleColor: Colors.white24,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
        ),
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: AppColors.surfaceDark,
        surfaceTintColor: Colors.transparent,
        indicatorColor: colorScheme.primary.withValues(alpha: 0.18),
        elevation: 0,
        labelTextStyle: WidgetStateProperty.resolveWith((states) {
          final selected = states.contains(WidgetState.selected);
          return TextStyle(
            fontSize: 12,
            fontWeight: selected ? FontWeight.w600 : FontWeight.w400,
            color: selected ? colorScheme.primary : Colors.white54,
          );
        }),
        iconTheme: WidgetStateProperty.resolveWith((states) {
          final selected = states.contains(WidgetState.selected);
          return IconThemeData(color: selected ? colorScheme.primary : Colors.white54);
        }),
      ),
      dividerColor: Colors.white12,
      iconTheme: IconThemeData(color: colorScheme.onSurface),
    );
  }
}
