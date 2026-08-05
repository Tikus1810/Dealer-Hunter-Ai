"""DealBrain analyzer modules (Band 05 architecture): Price Analyzer, Seller
Analyzer, Specification Analyzer, Risk Analyzer, Repair-Feasibility Analyzer.

Each is pure (no I/O, no framework dependency) and independently testable —
takes domain data in, returns an `AnalyzerOutput` with its explanation
factors. Nothing here is a "hidden rule": every number that moves the score
comes with a human-readable reason (Band 05: "No hidden scoring rules").

v1 scoring weights below are a reasonable, documented starting point, not a
handed-down spec — Band 05/06 define principles (explainable, deterministic,
versioned) but not concrete formulas. Expect to tune these constants once
real usage data exists; that's exactly what `scoring_version` is for.
"""

from __future__ import annotations

import statistics

from app.modules.offers.domain.entities import Offer
from app.modules.repair.domain.entities import RepairReport
from app.modules.scoring.domain.entities import AnalyzerOutput, ExplanationFactor

_POSITIVE_CONDITION_KEYWORDS = (
    "neu",
    "wie neu",
    "ovp",
    "versiegelt",
    "originalverpackt",
    "kaum benutzt",
    "top zustand",
    "einwandfrei",
)
_NEGATIVE_CONDITION_KEYWORDS = (
    "defekt",
    "beschädigt",
    "bastler",
    "ersatzteil",
    "ersatzteilspender",
    "riss",
    "wasserschaden",
    "displayschaden",
    "akku defekt",
)
_SCAM_PATTERN_KEYWORDS = (
    "vorkasse",
    "western union",
    "nur überweisung",
    "keine besichtigung",
    "paypal freunde",
    "familie und freunde",
    "versand ins ausland",
)


class PriceAnalyzer:
    """Band 05 primary factor: 'Price competitiveness'. Input: 'Estimated
    market value' is itself derived here from comparable active listings in
    the same category — DealBrain has no external pricing data source
    (Band 07 doesn't provide one; see README 'Known gaps')."""

    MIN_COMPARABLES_FOR_FULL_CONFIDENCE = 3
    MAX_SCORE_SWING = 40.0

    def analyze(self, offer: Offer, comparable_prices: list[float]) -> tuple[AnalyzerOutput, float]:
        """Returns (analyzer output, estimated market value)."""
        prices = [p for p in comparable_prices if p > 0]

        if len(prices) >= self.MIN_COMPARABLES_FOR_FULL_CONFIDENCE:
            market_value = statistics.median(prices)
            confidence = 1.0
            basis = f"median of {len(prices)} comparable {offer.category.value} listings"
        elif prices:
            market_value = statistics.median(prices)
            confidence = 0.5
            basis = (
                f"median of only {len(prices)} comparable listing(s) "
                f"(below {self.MIN_COMPARABLES_FOR_FULL_CONFIDENCE}, confidence reduced)"
            )
        else:
            market_value = offer.price_amount
            confidence = 0.2
            basis = "no comparable listings available; using this offer's own price as the baseline"

        discount_ratio = (
            0.0 if market_value <= 0 else (market_value - offer.price_amount) / market_value
        )
        score_contribution = max(
            -self.MAX_SCORE_SWING, min(self.MAX_SCORE_SWING, discount_ratio * 200)
        )

        factor = ExplanationFactor(
            name="price_competitiveness",
            impact=round(score_contribution, 1),
            description=(
                f"Price {offer.price_amount:.0f} {offer.price_currency} vs. estimated market "
                f"value {market_value:.0f} {offer.price_currency} "
                f"({discount_ratio:+.0%}); {basis}."
            ),
        )
        return AnalyzerOutput(score_contribution, confidence, [factor]), market_value


class SpecificationAnalyzer:
    """Band 05 factors: 'Device condition', 'Completeness of listing'.
    Deliberately simple keyword/heuristic matching for v1 — Vision AI
    (Task #8) will provide much stronger condition signals from images."""

    def analyze(self, offer: Offer) -> AnalyzerOutput:
        factors: list[ExplanationFactor] = []
        score = 0.0
        confidence = 1.0

        text = f"{offer.title} {offer.description}".lower()
        positive_hits = [kw for kw in _POSITIVE_CONDITION_KEYWORDS if kw in text]
        negative_hits = [kw for kw in _NEGATIVE_CONDITION_KEYWORDS if kw in text]

        if negative_hits:
            score -= 15.0
            factors.append(
                ExplanationFactor(
                    "condition_risk_keywords",
                    -15.0,
                    f"Listing text mentions possible defects: {', '.join(negative_hits)}.",
                )
            )
        elif positive_hits:
            score += 8.0
            factors.append(
                ExplanationFactor(
                    "condition_positive_keywords",
                    8.0,
                    f"Listing text suggests good condition: {', '.join(positive_hits)}.",
                )
            )
        else:
            confidence -= 0.2
            factors.append(
                ExplanationFactor(
                    "condition_unclear",
                    0.0,
                    "No explicit condition information found in title/description.",
                )
            )

        image_count = len(offer.images)
        if image_count == 0:
            score -= 10.0
            confidence -= 0.3
            factors.append(
                ExplanationFactor(
                    "no_images", -10.0, "Listing has no images — condition cannot be verified."
                )
            )
        elif image_count < 3:
            score -= 3.0
            factors.append(
                ExplanationFactor("few_images", -3.0, f"Only {image_count} image(s) provided.")
            )
        else:
            score += 4.0
            factors.append(
                ExplanationFactor("sufficient_images", 4.0, f"{image_count} images provided.")
            )

        if len(offer.description.strip()) < 20:
            score -= 5.0
            confidence -= 0.1
            factors.append(
                ExplanationFactor(
                    "thin_description", -5.0, "Description is very short or missing."
                )
            )

        return AnalyzerOutput(score, max(0.0, confidence), factors)


class SellerAnalyzer:
    """Band 05 factor: 'Seller confidence'. Only `OfferSource.EBAY` exposes a
    numeric feedback rating today; every Kleinanzeigen offer comes through
    with `seller_rating=None`, which correctly reduces confidence rather
    than being scored as if it were a bad rating (Band 05: unknown values
    reduce confidence, not correctness)."""

    def analyze(self, offer: Offer) -> AnalyzerOutput:
        if offer.seller_rating is None:
            factor = ExplanationFactor(
                "seller_rating_unavailable",
                0.0,
                f"No seller rating available from {offer.source.value}.",
            )
            return AnalyzerOutput(0.0, 0.6, [factor])

        rating = offer.seller_rating  # 0-100 percentage
        # 100% -> +10, 95% -> +2.5, below ~90% starts costing points.
        score = max(-20.0, min(10.0, (rating - 90.0) * 2))
        factor = ExplanationFactor(
            "seller_rating", round(score, 1), f"Seller feedback rating: {rating:.1f}%."
        )
        return AnalyzerOutput(score, 1.0, [factor])


class RiskAnalyzer:
    """Band 05 factor: 'Risk indicators'."""

    def analyze(self, offer: Offer) -> AnalyzerOutput:
        factors: list[ExplanationFactor] = []
        score = 0.0
        confidence = 1.0
        text = f"{offer.title} {offer.description}".lower()

        scam_hits = [kw for kw in _SCAM_PATTERN_KEYWORDS if kw in text]
        if scam_hits:
            score -= 30.0
            confidence -= 0.4
            factors.append(
                ExplanationFactor(
                    "scam_pattern_keywords",
                    -30.0,
                    f"Text contains common scam-listing phrasing: {', '.join(scam_hits)}.",
                )
            )

        if not offer.location:
            score -= 5.0
            confidence -= 0.1
            factors.append(
                ExplanationFactor("missing_location", -5.0, "No seller location provided.")
            )

        if offer.price_amount < 1.0:
            score -= 20.0
            confidence -= 0.2
            factors.append(
                ExplanationFactor(
                    "implausible_price",
                    -20.0,
                    "Price is implausibly low (<1 currency unit) for this category.",
                )
            )

        if not factors:
            factors.append(
                ExplanationFactor("no_risk_indicators", 0.0, "No known risk indicators detected.")
            )

        return AnalyzerOutput(score, max(0.0, confidence), factors)


class RepairFeasibilityAnalyzer:
    """Band 05 factor: 'Repair feasibility', fed by an actual RepairBrain
    `RepairReport` (Task #7). Contribution is scaled modestly — DealBrain is
    a purchase-decision tool, not a repair-cost calculator."""

    def analyze(self, repair_report: RepairReport) -> AnalyzerOutput:
        contribution = (repair_report.repair_score - 50) / 5  # 100->+10, 0->-10
        factor = ExplanationFactor(
            "repair_feasibility",
            round(contribution, 1),
            f"RepairBrain repair score: {repair_report.repair_score}/100 "
            f"({repair_report.difficulty.value}).",
        )
        return AnalyzerOutput(contribution, 0.9, [factor])
