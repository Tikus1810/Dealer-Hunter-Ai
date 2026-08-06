/// Mirrors the backend's `OfferResponse`
/// (`backend/app/modules/offers/presentation/schemas.py`).
class Offer {
  const Offer({
    required this.id,
    required this.source,
    required this.sourceListingId,
    required this.title,
    required this.description,
    required this.priceAmount,
    required this.priceCurrency,
    required this.category,
    required this.images,
    required this.url,
    this.location,
    this.createdAt,
    this.fetchedAt,
  });

  final String id;
  final String source;
  final String sourceListingId;
  final String title;
  final String description;
  final double priceAmount;
  final String priceCurrency;
  final String category;
  final List<String> images;
  final String url;
  final String? location;
  final DateTime? createdAt;
  final DateTime? fetchedAt;

  factory Offer.fromJson(Map<String, dynamic> json) {
    return Offer(
      id: json['id'] as String,
      source: json['source'] as String,
      sourceListingId: json['source_listing_id'] as String,
      title: json['title'] as String,
      description: json['description'] as String,
      priceAmount: (json['price_amount'] as num).toDouble(),
      priceCurrency: json['price_currency'] as String,
      category: json['category'] as String,
      images: (json['images'] as List<dynamic>).cast<String>(),
      url: json['url'] as String,
      location: json['location'] as String?,
      createdAt: _parseDateTime(json['created_at']),
      fetchedAt: _parseDateTime(json['fetched_at']),
    );
  }

  static DateTime? _parseDateTime(Object? value) =>
      value is String ? DateTime.parse(value) : null;
}

/// One page of offers, mirroring `OfferListResponse`.
class OfferPage {
  const OfferPage({
    required this.items,
    required this.total,
    required this.page,
    required this.pageSize,
  });

  final List<Offer> items;
  final int total;
  final int page;
  final int pageSize;

  bool get hasPreviousPage => page > 1;

  bool get hasNextPage => page * pageSize < total;

  factory OfferPage.fromJson(Map<String, dynamic> json) {
    final rawItems = json['items'] as List<dynamic>? ?? const [];
    return OfferPage(
      items: rawItems.map((e) => Offer.fromJson(e as Map<String, dynamic>)).toList(),
      total: json['total'] as int? ?? 0,
      page: json['page'] as int? ?? 1,
      pageSize: json['page_size'] as int? ?? 20,
    );
  }
}
