"""Fault Analyzer (Band 06 architecture module).

Detects likely repair scenarios from structured offer data: explicitly
`reported_defects` are confirmed facts; matches against listing text are
inferred assumptions, kept clearly distinct (Band 06: "Detect likely repair
scenarios from structured offer data", "Separate confirmed facts from
assumptions").
"""

from __future__ import annotations

from app.modules.offers.domain.entities import Offer
from app.modules.repair.domain.catalog import FAULT_KEYWORDS
from app.modules.repair.domain.entities import DetectedFault


class FaultAnalyzer:
    def analyze(self, offer: Offer, reported_defects: list[str]) -> list[DetectedFault]:
        faults: list[DetectedFault] = []
        confirmed_categories: set[str] = set()

        for defect in reported_defects:
            category = self._categorize(defect)
            if category is None:
                # Unrecognized free-text defect — still a confirmed fact,
                # just not mappable to our parts/time/tools catalog.
                category = "other"
            faults.append(DetectedFault(category=category, is_confirmed=True, detail=defect))
            confirmed_categories.add(category)

        text = f"{offer.title} {offer.description}".lower()
        inferred_categories: set[str] = set()
        for phrase, category in FAULT_KEYWORDS.items():
            if phrase in text and category not in confirmed_categories:
                if category in inferred_categories:
                    continue  # already recorded this inferred category once
                inferred_categories.add(category)
                faults.append(DetectedFault(category=category, is_confirmed=False, detail=phrase))

        return faults

    @staticmethod
    def _categorize(defect_text: str) -> str | None:
        lowered = defect_text.lower()
        for phrase, category in FAULT_KEYWORDS.items():
            if phrase in lowered:
                return category
        return None
