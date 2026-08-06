/// Mirrors the backend's `ReplacementPartResponse`.
class ReplacementPart {
  const ReplacementPart({
    required this.name,
    required this.estimatedPrice,
    required this.availability,
  });

  final String name;
  final double estimatedPrice;
  final String availability;

  factory ReplacementPart.fromJson(Map<String, dynamic> json) {
    return ReplacementPart(
      name: json['name'] as String,
      estimatedPrice: (json['estimated_price'] as num).toDouble(),
      availability: json['availability'] as String,
    );
  }
}

/// Mirrors the backend's `RepairReportResponse`
/// (`backend/app/modules/repair/presentation/schemas.py`).
class RepairReport {
  const RepairReport({
    required this.offerId,
    required this.repairScore,
    required this.estimatedRepairCost,
    required this.estimatedRepairTimeHours,
    required this.difficulty,
    required this.requiredTools,
    required this.compatibleParts,
    required this.riskNotes,
    required this.summary,
    required this.reportVersion,
  });

  final String offerId;
  final int repairScore;
  final double estimatedRepairCost;
  final double estimatedRepairTimeHours;
  final String difficulty;
  final List<String> requiredTools;
  final List<ReplacementPart> compatibleParts;
  final List<String> riskNotes;
  final String summary;
  final String reportVersion;

  factory RepairReport.fromJson(Map<String, dynamic> json) {
    final rawParts = json['compatible_parts'] as List<dynamic>? ?? const [];
    return RepairReport(
      offerId: json['offer_id'] as String,
      repairScore: json['repair_score'] as int,
      estimatedRepairCost: (json['estimated_repair_cost'] as num).toDouble(),
      estimatedRepairTimeHours: (json['estimated_repair_time_hours'] as num).toDouble(),
      difficulty: json['difficulty'] as String,
      requiredTools: (json['required_tools'] as List<dynamic>? ?? const []).cast<String>(),
      compatibleParts:
          rawParts.map((e) => ReplacementPart.fromJson(e as Map<String, dynamic>)).toList(),
      riskNotes: (json['risk_notes'] as List<dynamic>? ?? const []).cast<String>(),
      summary: json['summary'] as String,
      reportVersion: json['report_version'] as String,
    );
  }
}
