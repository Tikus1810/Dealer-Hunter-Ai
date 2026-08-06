/// Typography tokens (Band 18: design system typography). Left at the
/// platform default for now — `null` keeps Material 3's default type scale
/// (Roboto/SF) rather than guessing at a brand typeface; Task #19
/// (Branding) is where a real font family gets chosen and wired in here.
class AppTypography {
  const AppTypography._();

  static const String? fontFamily = null;
}
