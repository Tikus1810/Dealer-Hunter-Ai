"""RepairBrain domain entities (Band 06)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import StrEnum


class RepairDifficulty(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


@dataclass(frozen=True, slots=True)
class ReplacementPart:
    name: str
    estimated_price: float
    availability: str  # e.g. "in_stock", "limited", "unknown"


@dataclass(frozen=True, slots=True)
class DetectedFault:
    """One fault detected by `FaultAnalyzer` (Band 06 functional requirement:
    "Separate confirmed facts from assumptions")."""

    category: str  # normalized, e.g. "display", "battery" — see catalog.py
    is_confirmed: bool  # True: explicitly in reported_defects; False: inferred from text
    detail: str  # the original reported string or matched listing phrase


@dataclass(frozen=True, slots=True)
class RepairReport:
    offer_id: uuid.UUID
    repair_score: int  # 0-100, higher = more worthwhile to repair
    estimated_repair_cost: float
    estimated_repair_time_hours: float
    difficulty: RepairDifficulty
    required_tools: list[str] = field(default_factory=list)
    compatible_parts: list[ReplacementPart] = field(default_factory=list)
    risk_notes: list[str] = field(default_factory=list)
    summary: str = ""
    report_version: str = "1.0.0"
