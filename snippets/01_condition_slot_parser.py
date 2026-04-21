"""Public snippet: condition slot parser for architecture-law queries.

- Demonstrates deterministic slot extraction before LLM reasoning.
- Intended for portfolio visibility (not full production code).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


REQUIRED_SLOTS = [
    "address",
    "usage",
    "site_area_m2",
    "gross_floor_area_m2",
    "floors",
    "max_height_m",
    "road_width_m",
]


@dataclass
class QueryState:
    user_query: str
    confirmed_conditions: dict[str, object] = field(default_factory=dict)
    missing_slots: list[str] = field(default_factory=list)


def _extract_number(text: str, label: str) -> float | None:
    pattern = rf"{label}\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)"
    m = re.search(pattern, text)
    return float(m.group(1)) if m else None


def parse_conditions(state: QueryState) -> QueryState:
    query = state.user_query
    slots = dict(state.confirmed_conditions)

    addr_match = re.search(r"([가-힣]+(?:시|도)\s*[가-힣]+(?:시|군|구))", query)
    if addr_match:
        slots["address"] = addr_match.group(1)

    usage_match = re.search(r"(문화 및 집회시설|업무시설|주거시설|공동주택)", query)
    if usage_match:
        slots["usage"] = usage_match.group(1)

    floor_match = re.search(r"(지하\d+층\s*지상\d+층|지상\d+층)", query)
    if floor_match:
        slots["floors"] = floor_match.group(1)

    label_map = {
        "대지면적": "site_area_m2",
        "연면적": "gross_floor_area_m2",
        "최고높이": "max_height_m",
        "도로너비": "road_width_m",
    }
    for label, key in label_map.items():
        value = _extract_number(query, label)
        if value is not None:
            slots[key] = value

    state.confirmed_conditions = slots
    state.missing_slots = [k for k in REQUIRED_SLOTS if k not in slots]
    return state


if __name__ == "__main__":
    s = QueryState(user_query="서울시 강남구, 업무시설, 대지면적 300, 연면적 500, 지상10층")
    out = parse_conditions(s)
    print("conditions:", out.confirmed_conditions)
    print("missing:", out.missing_slots)
