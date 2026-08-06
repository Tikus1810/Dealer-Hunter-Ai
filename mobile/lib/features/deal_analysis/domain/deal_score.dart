/// Mirrors the backend's `ExplanationFactorResponse`.
class ExplanationFactor {
  const ExplanationFactor({required this.name, required this.impact, required this.description});

  final String name;
  final double impact;
  final String description;

  factory ExplanationFactor.fromJson(Map<String, dynamic> json) {
    return ExplanationFactor(
      name: json['name'] as String,
      impact: (json['impact'] as num).toDouble(),
      description: json['description'] as String,
    );
  }
}

/// Mirrors the backend's `DealScoreResponse`
/// (`backend/app/modules/scoring/presentation/schemas.py`).
class DealScore {
  const DealScore({
    required this.offerId,
    required this.score,
    required this.confidence,
    required this.estimatedMarketValue,
    required this.estimatedTotalCost,
    required this.recommendation,
    required this.explanation,
    required this.scoringVersion,
  });

  final String offerId;
  final int score;
  final double confidence;
  final double estimatedMarketValue;
  final double estimatedTotalCost;
  final String recommendation;
  final List<ExplanationFactor> explanation;
  final String scoringVersion;

  factory DealScore.fromJson(Map<String, dynamic> json) {
    final rawExplanation = json['explanation'] as List<dynamic>? ?? const [];
    return DealScore(
      offerId: json['offer_id'] as String,
      score: json['score'] as int,
      confidence: (json['confidence'] as num).toDouble(),
      estimatedMarketValue: (json['estimated_market_value'] as num).toDouble(),
      estimatedTotalCost: (json['estimated_total_cost'] as num).toDouble(),
      recommendation: json['recommendation'] as String,
      explanation: rawExplanation
          .map((e) => ExplanationFactor.fromJson(e as Map<String, dynamic>))
          .toList(),
      scoringVersion: json['scoring_version'] as String,
    );
  }
}
