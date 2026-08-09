import 'package:flutter/cupertino.dart';

import '../theme/app_colors.dart';

/// The one shared `CupertinoThemeData` every `CupertinoAlertDialog` in the
/// app should render under.
///
/// `showCupertinoDialog` otherwise resolves its look from the *host OS's*
/// light/dark setting (`MediaQuery.platformBrightness`), not this app's own
/// forced-dark `AppTheme` (see that file's docstring on why light/dark
/// aren't a conventional pair here) — without pinning this explicitly, an
/// alert could render as a stray white iOS dialog on top of this app's
/// black page if the device happens to be in light mode.
const appCupertinoTheme = CupertinoThemeData(
  brightness: Brightness.dark,
  primaryColor: AppColors.seed,
  scaffoldBackgroundColor: AppColors.backgroundBlack,
  barBackgroundColor: AppColors.surfaceDark,
);

/// Drop-in replacement for `showCupertinoDialog` that wraps the built
/// dialog in [appCupertinoTheme] — use this (not `showDialog`+`AlertDialog`
/// or a bare `showCupertinoDialog`) for any new confirm/alert prompt so it
/// gets the real iOS alert look-and-feel and stays on-brand automatically.
Future<T?> showAppCupertinoDialog<T>({
  required BuildContext context,
  required WidgetBuilder builder,
  bool barrierDismissible = true,
}) {
  return showCupertinoDialog<T>(
    context: context,
    barrierDismissible: barrierDismissible,
    builder: (context) => CupertinoTheme(data: appCupertinoTheme, child: Builder(builder: builder)),
  );
}
