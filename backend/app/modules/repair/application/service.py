"""RepairBrain application service — implements `RepairAnalysisServiceProtocol`.

Orchestrates the Band 06 architecture: Fault Analyzer -> Parts Resolver +
Time Estimator -> Cost Estimator -> Repair Scoring Engine -> Recommendation
Generator -> persist. No estimation math lives here.
"""

from __future__ import annotations

import uuid

from app.core.exceptions import NotFoundError
from app.modules.offers.application.interfaces import OfferRepositoryProtocol
from app.modules.repair.application.interfaces import RepairReportRepositoryProtocol
from app.modules.repair.domain.cost_estimator import CostEstimator
from app.modules.repair.domain.entities import RepairReport
from app.modules.repair.domain.fault_analyzer import FaultAnalyzer
from app.modules.repair.domain.parts_resolver import PartsResolver
from app.modules.repair.domain.recommendation import RecommendationGenerator
from app.modules.repair.domain.scoring_engine import REPORT_VERSION, RepairScoringEngine
from app.modules.repair.domain.time_estimator import TimeEstimator


class RepairBrainService:
    def __init__(
        self,
        offers: OfferRepositoryProtocol,
        repair_reports: RepairReportRepositoryProtocol,
        *,
        fault_analyzer: FaultAnalyzer | None = None,
        parts_resolver: PartsResolver | None = None,
        time_estimator: TimeEstimator | None = None,
        cost_estimator: CostEstimator | None = None,
        scoring_engine: RepairScoringEngine | None = None,
        recommendation_generator: RecommendationGenerator | None = None,
    ) -> None:
        self._offers = offers
        self._repair_reports = repair_reports
        self._fault_analyzer = fault_analyzer or FaultAnalyzer()
        self._parts_resolver = parts_resolver or PartsResolver()
        self._time_estimator = time_estimator or TimeEstimator()
        self._cost_estimator = cost_estimator or CostEstimator()
        self._scoring_engine = scoring_engine or RepairScoringEngine()
        self._recommendation_generator = recommendation_generator or RecommendationGenerator()

    async def analyze(self, offer_id: uuid.UUID, *, reported_defects: list[str]) -> RepairReport:
        offer = await self._offers.get_by_id(offer_id)
        if offer is None:
            raise NotFoundError("offer not found", details={"offer_id": str(offer_id)})

        faults = self._fault_analyzer.analyze(offer, reported_defects)
        time_estimate = self._time_estimator.estimate(faults)
        parts = self._parts_resolver.resolve_parts(faults, offer.category)
        tools = self._parts_resolver.resolve_tools(faults)
        cost = self._cost_estimator.estimate(parts, time_estimate.hours)
        score = self._scoring_engine.score(faults, time_estimate.difficulty, cost)
        summary, risk_notes = self._recommendation_generator.summarize(
            faults, time_estimate.difficulty, score, cost, time_estimate.hours
        )

        report = RepairReport(
            offer_id=offer.id,
            repair_score=score,
            estimated_repair_cost=cost,
            estimated_repair_time_hours=time_estimate.hours,
            difficulty=time_estimate.difficulty,
            required_tools=tools,
            compatible_parts=parts,
            risk_notes=risk_notes,
            summary=summary,
            report_version=REPORT_VERSION,
        )
        await self._repair_reports.save(report)
        return report
