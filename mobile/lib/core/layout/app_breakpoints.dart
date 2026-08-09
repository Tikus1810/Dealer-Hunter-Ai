/// Width thresholds for adaptive layout (Band 04 redesign — Windows exe
/// support). A phone (even a large one, even rotated) never reaches
/// [desktop]; a resized Chrome window on a laptop or the Windows exe's
/// own window does. Used to switch the primary navigation from a bottom
/// tab bar (mobile/touch idiom) to a side rail (the desktop-app idiom) —
/// see `AppShell` — plus a few content grids that would otherwise stay a
/// fixed mobile column count and leave the extra width empty.
class AppBreakpoints {
  const AppBreakpoints._();

  /// Material 3's own "expanded" window-size-class threshold.
  static const double desktop = 840;
}
