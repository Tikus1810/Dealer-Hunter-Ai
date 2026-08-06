/// Mirrors the backend's `FavoriteResponse`
/// (`backend/app/modules/offers/presentation/schemas.py`). Note it only
/// carries the offer id, not the offer itself — the favorites screen fetches
/// each offer's details separately (see `FavoritesController`'s doc comment).
class Favorite {
  const Favorite({required this.id, required this.offerId, this.createdAt});

  final String id;
  final String offerId;
  final DateTime? createdAt;

  factory Favorite.fromJson(Map<String, dynamic> json) {
    final createdAtRaw = json['created_at'];
    return Favorite(
      id: json['id'] as String,
      offerId: json['offer_id'] as String,
      createdAt: createdAtRaw is String ? DateTime.parse(createdAtRaw) : null,
    );
  }
}
