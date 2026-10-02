"""Best-effort product matching across retailers by parsed specs.

There's no shared product ID across Newegg/Amazon/PCPartPicker, so
cross-site price comparison is approximate: two listings are treated as
"the same configuration" when they parse to the same (memory_type,
brand, total_capacity_gb, speed_mt_s) tuple. This can conflate genuinely
different SKUs that happen to share those specs - different CAS latency,
heatspreader/RGB variant, kit layout (2x16GB vs 4x8GB at the same total
capacity) - so it's a "comparable configuration" match, not proof of an
identical physical product. Good enough for "what's this roughly going
for elsewhere," not for guaranteeing the exact same kit.
"""
from __future__ import annotations

import re
from typing import Optional

# None of these substrings collide with each other, so simple substring
# matching (no word boundaries) is enough and also catches names where a
# scrape artifact glued a preceding word onto the brand (e.g. a retailer's
# "Used" condition badge becoming "...NewPatriot Viper Elite...").
KNOWN_BRANDS = [
    "g.skill",
    "gskill",
    "corsair",
    "team",  # catches TeamGroup's sub-brand lines too: T-Force, T-Create, ...
    "patriot",
    "kingston",
    "crucial",
    "adata",
    "xpg",
    "pny",
    "nemix",
    "black diamond",
    "mushkin",
    "silicon power",
    "timetec",
]

_BRAND_ALIASES = {
    "g.skill": "gskill",
    "black diamond": "blackdiamond",
    "silicon power": "siliconpower",
}

_CAPACITY_RE = re.compile(r"(\d+)\s*GB\b", re.IGNORECASE)
_SPEED_RE = re.compile(r"DDR[45][\s-]?(\d{3,5})", re.IGNORECASE)


def extract_brand(name: str) -> Optional[str]:
    lower = name.lower()
    for brand in KNOWN_BRANDS:
        if brand in lower:
            return _BRAND_ALIASES.get(brand, brand)
    return None


def extract_capacity_gb(name: str) -> Optional[int]:
    """Total kit capacity - every retailer states this before any (N x
    MGB) breakdown, so the first "<N>GB" match in the name is the total.
    """
    match = _CAPACITY_RE.search(name)
    return int(match.group(1)) if match else None


def extract_speed_mt_s(name: str) -> Optional[int]:
    match = _SPEED_RE.search(name)
    return int(match.group(1)) if match else None


def spec_key(memory_type: str, name: str) -> Optional[tuple]:
    """A (memory_type, brand, capacity_gb, speed_mt_s) tuple, or None if
    any piece couldn't be parsed from the name (too little to match on).
    """
    brand = extract_brand(name)
    capacity = extract_capacity_gb(name)
    speed = extract_speed_mt_s(name)
    if not (brand and capacity and speed):
        return None
    return (memory_type, brand, capacity, speed)
