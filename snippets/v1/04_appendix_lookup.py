"""Public snippet: appendix taxonomy lookup.

Matching strategy:
1) exact match
2) alias match
3) keyword overlap score
"""

from __future__ import annotations

import re


def tokenize(text: str) -> set[str]:
    return {t for t in re.split(r"[^0-9A-Za-z가-힣]+", text.lower()) if t}


def lookup_appendix(terms: list[dict], query: str, top_k: int = 5) -> list[dict]:
    q = query.strip().lower()
    if not q:
        return []

    q_tokens = tokenize(q)
    exact: list[dict] = []
    alias: list[dict] = []
    fuzzy: list[tuple[float, dict]] = []

    for term in terms:
        category = str(term.get("category", ""))
        subcategory = str(term.get("subcategory", ""))
        aliases = [str(a) for a in term.get("aliases", [])]
        desc = str(term.get("description", ""))

        if q in category.lower() or q in subcategory.lower():
            exact.append(term)
            continue

        if any(q in a.lower() or a.lower() in q for a in aliases):
            alias.append(term)
            continue

        doc_tokens = tokenize(" ".join([category, subcategory, " ".join(aliases), desc]))
        if not doc_tokens:
            continue

        score = len(q_tokens & doc_tokens) / len(q_tokens | doc_tokens) if q_tokens else 0.0
        if score > 0:
            fuzzy.append((score, term))

    fuzzy.sort(key=lambda x: x[0], reverse=True)
    merged = exact + alias + [t for _, t in fuzzy]

    out = []
    seen = set()
    for row in merged:
        key = (row.get("category"), row.get("subcategory"))
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
        if len(out) >= top_k:
            break

    return out
