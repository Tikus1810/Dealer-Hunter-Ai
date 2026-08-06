/// Named route paths (Band 04: "Deep linking ready" — every destination
/// gets a real URL-shaped path, not an opaque page index). One constant
/// per Band 04 "Core Feature".
class RoutePaths {
  const RoutePaths._();

  static const login = '/login';
  static const register = '/register';
  static const dashboard = '/';
  static const searchProfiles = '/search-profiles';
  static const offers = '/offers';
  static const offerDetail = '/offers/:offerId';
  static const dealAnalysis = '/offers/:offerId/deal-analysis';
  static const repairAnalysis = '/offers/:offerId/repair-analysis';
  static const favorites = '/favorites';
  static const notifications = '/notifications';
  static const settings = '/settings';

  static String offerDetailPath(String offerId) => '/offers/$offerId';

  static String dealAnalysisPath(String offerId) => '/offers/$offerId/deal-analysis';

  static String repairAnalysisPath(String offerId) => '/offers/$offerId/repair-analysis';
}
