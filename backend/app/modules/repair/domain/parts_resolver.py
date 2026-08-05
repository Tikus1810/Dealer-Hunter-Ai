"""Parts Resolver (Band 06 architecture module).

Independent from scoring (Band 06: "Keep parts lookup independent from
scoring") — takes detected faults, returns replacement parts and the tools
needed to install them. Pure catalog lookup, no I/O.
"""

from __future__ import annotations

from app.modules.offers.domain.entities import OfferCategory
from app.modules.repair.domain.catalog import DEFAULT_TOOLS, FAULT_TOOLS, PART_CATALOG
from app.modules.repair.domain.entities import DetectedFault, ReplacementPart


class PartsResolver:
    def resolve_parts(
        self, faults: list[DetectedFault], category: OfferCategory
    ) -> list[ReplacementPart]:
        parts: list[ReplacementPart] = []
        seen_names: set[str] = set()

        for fault in faults:
            part = PART_CATALOG.get((category, fault.category))
            if part is None:
                part = ReplacementPart(
                    name=f"Unidentified part for '{fault.category}'",
                    estimated_price=0.0,
                    availability="unknown",
                )
            if part.name not in seen_names:
                parts.append(part)
                seen_names.add(part.name)

        return parts

    def resolve_tools(self, faults: list[DetectedFault]) -> list[str]:
        tools: list[str] = []
        for fault in faults:
            for tool in FAULT_TOOLS.get(fault.category, DEFAULT_TOOLS):
                if tool not in tools:
                    tools.append(tool)
        return tools or list(DEFAULT_TOOLS)
