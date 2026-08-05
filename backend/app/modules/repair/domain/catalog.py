"""Shared static reference data for RepairBrain's estimators (Band 06).

Every table here is keyed by a normalized *fault category* (e.g. "display",
"battery") so `FaultAnalyzer`, `PartsResolver` and `TimeEstimator` share one
taxonomy instead of each inventing their own.

These are indicative, hand-maintained reference values — RepairBrain has no
live parts-supplier or repair-shop pricing feed (same honesty note as
DealBrain's PriceAnalyzer: no such data source exists yet). Extending to a
new device category (Band 06 quality requirement) means adding rows here,
not touching any estimator's logic.
"""

from __future__ import annotations

from app.modules.offers.domain.entities import OfferCategory
from app.modules.repair.domain.entities import RepairDifficulty, ReplacementPart

# Listing-text phrase -> normalized fault category. Checked as substrings of
# a lowercased "title description" blob.
FAULT_KEYWORDS: dict[str, str] = {
    "display defekt": "display",
    "displayschaden": "display",
    "riss im display": "display",
    "gesprungenes display": "display",
    "kein bild": "display",
    "akku defekt": "battery",
    "akku schwach": "battery",
    "batterie defekt": "battery",
    "schwache batterie": "battery",
    "wasserschaden": "water_damage",
    "geht nicht an": "power",
    "startet nicht": "power",
    "lädt nicht": "charging_port",
    "ladebuchse defekt": "charging_port",
    "tastatur defekt": "keyboard",
    "einzelne tasten": "keyboard",
    "kamera defekt": "camera",
    "lautsprecher defekt": "speaker",
    "kein ton": "speaker",
    "knickt": "hinge",
    "scharnier": "hinge",
}

FAULT_TIME_HOURS: dict[str, float] = {
    "display": 1.0,
    "battery": 0.5,
    "keyboard": 0.75,
    "charging_port": 1.5,
    "camera": 0.5,
    "speaker": 0.5,
    "hinge": 1.5,
    "water_damage": 3.0,
    "power": 2.5,
}
DEFAULT_FAULT_TIME_HOURS = 1.0

FAULT_DIFFICULTY: dict[str, RepairDifficulty] = {
    "battery": RepairDifficulty.BEGINNER,
    "keyboard": RepairDifficulty.BEGINNER,
    "camera": RepairDifficulty.BEGINNER,
    "speaker": RepairDifficulty.BEGINNER,
    "display": RepairDifficulty.INTERMEDIATE,
    "charging_port": RepairDifficulty.INTERMEDIATE,
    "hinge": RepairDifficulty.INTERMEDIATE,
    "power": RepairDifficulty.ADVANCED,
    "water_damage": RepairDifficulty.ADVANCED,
}
DEFAULT_FAULT_DIFFICULTY = RepairDifficulty.INTERMEDIATE
_DIFFICULTY_RANK: dict[RepairDifficulty, int] = {
    RepairDifficulty.BEGINNER: 0,
    RepairDifficulty.INTERMEDIATE: 1,
    RepairDifficulty.ADVANCED: 2,
}

FAULT_TOOLS: dict[str, list[str]] = {
    "display": ["Pentalobe/Torx screwdriver set", "Plastic pry tools", "Suction cup"],
    "battery": ["Pentalobe/Torx screwdriver set", "Plastic pry tools", "Adhesive strips"],
    "keyboard": ["Torx screwdriver set", "Plastic pry tools"],
    "charging_port": ["Precision screwdriver set", "Soldering iron"],
    "camera": ["Precision screwdriver set", "Plastic pry tools"],
    "speaker": ["Precision screwdriver set"],
    "hinge": ["Torx screwdriver set", "Heat gun"],
    "water_damage": ["Isopropyl alcohol", "Ultrasonic cleaner", "Multimeter", "Soldering station"],
    "power": ["Multimeter", "Soldering station"],
}
DEFAULT_TOOLS = ["Precision screwdriver set", "Plastic pry tools"]

_MB = OfferCategory.MACBOOK
_WL = OfferCategory.WINDOWS_LAPTOP
_IP = OfferCategory.IPHONE
_GC = OfferCategory.GAME_CONSOLE
_RP = ReplacementPart

PART_CATALOG: dict[tuple[OfferCategory, str], ReplacementPart] = {
    (_MB, "display"): _RP("MacBook display assembly", 220.0, "limited"),
    (_MB, "battery"): _RP("MacBook replacement battery", 70.0, "in_stock"),
    (_MB, "keyboard"): _RP("MacBook keyboard/top case", 150.0, "limited"),
    (_MB, "charging_port"): _RP("MagSafe/USB-C board", 45.0, "in_stock"),
    (_MB, "camera"): _RP("Webcam module", 25.0, "in_stock"),
    (_MB, "speaker"): _RP("Speaker assembly", 30.0, "in_stock"),
    (_MB, "hinge"): _RP("Display hinge clutch", 40.0, "limited"),
    (_MB, "water_damage"): _RP("Logic board diagnostic/repair", 180.0, "unknown"),
    (_MB, "power"): _RP("Logic board diagnostic/repair", 180.0, "unknown"),
    (_WL, "display"): _RP("Laptop display panel", 90.0, "in_stock"),
    (_WL, "battery"): _RP("Laptop replacement battery", 45.0, "in_stock"),
    (_WL, "keyboard"): _RP("Laptop keyboard", 30.0, "in_stock"),
    (_WL, "charging_port"): _RP("DC power jack", 15.0, "in_stock"),
    (_WL, "camera"): _RP("Webcam module", 15.0, "in_stock"),
    (_WL, "speaker"): _RP("Speaker set", 20.0, "in_stock"),
    (_WL, "hinge"): _RP("Display hinge set", 25.0, "in_stock"),
    (_WL, "water_damage"): _RP("Motherboard diagnostic/repair", 100.0, "unknown"),
    (_WL, "power"): _RP("Motherboard diagnostic/repair", 100.0, "unknown"),
    (_IP, "display"): _RP("iPhone display assembly", 90.0, "in_stock"),
    (_IP, "battery"): _RP("iPhone replacement battery", 35.0, "in_stock"),
    (_IP, "camera"): _RP("Rear camera module", 55.0, "in_stock"),
    (_IP, "charging_port"): _RP("Charging port flex cable", 25.0, "in_stock"),
    (_IP, "speaker"): _RP("Speaker module", 20.0, "in_stock"),
    (_IP, "water_damage"): _RP("Logic board diagnostic/repair", 120.0, "unknown"),
    (_IP, "power"): _RP("Logic board diagnostic/repair", 120.0, "unknown"),
    (_GC, "power"): _RP("Power supply unit", 35.0, "in_stock"),
    (_GC, "display"): _RP("HDMI/video output board", 25.0, "limited"),
    (_GC, "hinge"): _RP("Disc drive assembly", 40.0, "limited"),
}


def difficulty_rank(difficulty: RepairDifficulty) -> int:
    return _DIFFICULTY_RANK[difficulty]
