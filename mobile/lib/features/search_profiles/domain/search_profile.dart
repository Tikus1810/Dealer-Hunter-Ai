/// Mirrors the backend's `SearchProfileResponse`
/// (`backend/app/modules/search/presentation/schemas.py`).
class SearchProfile {
  const SearchProfile({
    required this.id,
    required this.name,
    required this.category,
    this.keywords,
    this.minPrice,
    this.maxPrice,
    this.minDealScore,
    required this.notifyOnMatch,
    required this.isActive,
  });

  final String id;
  final String name;
  final String category;
  final String? keywords;
  final double? minPrice;
  final double? maxPrice;
  final int? minDealScore;
  final bool notifyOnMatch;
  final bool isActive;

  factory SearchProfile.fromJson(Map<String, dynamic> json) {
    return SearchProfile(
      id: json['id'] as String,
      name: json['name'] as String,
      category: json['category'] as String,
      keywords: json['keywords'] as String?,
      minPrice: (json['min_price'] as num?)?.toDouble(),
      maxPrice: (json['max_price'] as num?)?.toDouble(),
      minDealScore: json['min_deal_score'] as int?,
      notifyOnMatch: json['notify_on_match'] as bool,
      isActive: json['is_active'] as bool,
    );
  }
}
