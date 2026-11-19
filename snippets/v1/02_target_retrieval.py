"""Public snippet: target-aware retrieval flow.

- 1) Extract legal targets from query.
- 2) Retrieve per target.
- 3) Optional LLM filter to drop irrelevant chunks.
"""

from __future__ import annotations

from dataclasses import dataclass


TARGET_KEYWORDS = {
    "건축선": ["건축선", "도로경계", "후퇴선"],
    "건폐율": ["건폐율", "건축면적"],
    "용적률": ["용적률", "연면적"],
    "주차": ["주차", "주차대수", "주차장"],
}


@dataclass
class Chunk:
    law_name: str
    article_title: str
    content: str


def extract_targets(query: str) -> list[str]:
    found = [target for target, kws in TARGET_KEYWORDS.items() if any(k in query for k in kws)]
    return found or ["일반"]


def retrieve_targets_only(
    query: str,
    search_fn,
    llm_filter_fn=None,
    k_per_target: int = 5,
) -> dict[str, list[Chunk]]:
    targets = extract_targets(query)
    results: dict[str, list[Chunk]] = {}

    for target in targets:
        rows: list[Chunk] = search_fn(f"{query} {target}", k=k_per_target * 2)

        if llm_filter_fn is not None:
            rows = llm_filter_fn(query=query, target=target, rows=rows)

        results[target] = rows[:k_per_target]

    return results
