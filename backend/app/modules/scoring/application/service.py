"""DealBrain application service — implements `DealScoringServiceProtocol`.

Orchestrates the Band 05 architecture: gathers comparables, runs every
analyzer, combines them via the Scoring Engine, finalizes via the
Explanation Generator, persists, and returns the result. No scoring math
lives here — this module only wires the pieces together.
"""

from __future__ import annotations

import uuid

from app.core.exceptions import NotFoundError
from app.modules.offers.application.interfaces import OfferRepositoryProtocol
from app.modules.repair.domain.entities import RepairReport
from app.modules.scoring.application.interfaces import DealScoreRepositoryProtocol
from app.modules.scoring.domain.analyzers import (
    PriceAnalyzer,
    RepairFeasibilityAnalyzer,
    RiskAnalyzer,
    SellerAnalyzer,
    SpecificationAnalyzer,
)
from app.modules.scoring.domain.entities import AnalyzerOutput, DealScoreResult, ExplanationFactor
from app.modules.scoring.domain.explanation import ExplanationGenerator
from app.modules.scoring.domain.scoring_engine import ScoringEngine

_COMPARABLES_LIMIT = 50


class DealBrainService:
    def __init__(
        self,
        offers: OfferRepositoryProtocol,
        deal_scores: DealScoreRepositoryProtocol,
        *,
        price_analyzer: PriceAnalyzer | None = None,
        spec_analyzer: SpecificationAnalyzer | None = None,
        seller_analyzer: SellerAnalyzer | None = None,
        risk_analyzer: RiskAnalyzer | None = None,
        repair_analyzer: RepairFeasibilityAnalyzer | None = None,
        scoring_engine: ScoringEngine | None = None,
        explanation_generator: ExplanationGenerator | None = None,
    ) -> None:
        self._offers = offers
        self._deal_scores = deal_scores
        self._price_analyzer = price_analyzer or PriceAnalyzer()
        self._spec_analyzer = spec_analyzer or SpecificationAnalyzer()
        self._seller_analyzer = seller_analyzer or SellerAnalyzer()
        self._risk_analyzer = risk_analyzer or RiskAnalyzer()
        self._repair_analyzer = repair_analyzer or RepairFeasibilityAnalyzer()
        self._scoring_engine = scoring_engine or ScoringEngine()
        self._explanation_generator = explanation_generator or ExplanationGenerator()

    async def score_offer(
        self, offer_id: uuid.UUID, *, repair_report: RepairReport | None = None
    ) -> DealScoreResult:
        offer = await self._offers.get_by_id(offer_id)
        if offer is None:
            raise NotFoundError("offer not found", details={"offer_id": str(offer_id)})

        comparables = await self._offers.list_by_category(
            offer.category.value, limit=_COMPARABLES_LIMIT
        )
        comparable_prices = [o.price_amount for o in comparables if o.id != offer.id]

        price_output, market_value = self._price_analyzer.analyze(offer, comparable_prices)
        outputs: list[AnalyzerOutput] = [
            price_output,
            self._spec_analyzer.analyze(offer),
            self._seller_analyzer.analyze(offer),
            self._risk_analyzer.analyze(offer),
        ]

        if repair_report is not None:
            outputs.append(self._repair_analyzer.analyze(repair_report))
            total_cost = offer.price_amount + repair_report.estimated_repair_cost
        else:
            outputs.append(
                AnalyzerOutput(
                    0.0,
                    0.5,
                    [
                        ExplanationFactor(
                            "repair_assessment_unavailable",
                            0.0,
                            "No RepairBrain assessment available for this offer yet.",
                        )
                    ],
                )
            )
            total_cost = offer.price_amount

        result = self._scoring_engine.combine(
            offer, outputs, estimated_market_value=market_value, estimated_total_cost=total_cost
        )
        result = self._explanation_generator.finalize(result)

        await self._deal_scores.save(result)
        return result
