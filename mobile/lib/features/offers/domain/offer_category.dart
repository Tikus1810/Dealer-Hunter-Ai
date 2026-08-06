/// Mirrors the backend's `OfferCategory` enum
/// (`backend/app/modules/offers/domain/entities.py`) — `apiValue` must
/// match its `StrEnum` values exactly, since it's sent as a query param.
enum OfferCategory {
  windowsLaptop('windows_laptop', 'Windows-Laptop'),
  macbook('macbook', 'MacBook'),
  iphone('iphone', 'iPhone'),
  gameConsole('game_console', 'Spielekonsole');

  const OfferCategory(this.apiValue, this.label);

  final String apiValue;
  final String label;

  static OfferCategory fromApiValue(String value) {
    return OfferCategory.values.firstWhere(
      (category) => category.apiValue == value,
      orElse: () => throw ArgumentError('Unknown offer category: $value'),
    );
  }
}
