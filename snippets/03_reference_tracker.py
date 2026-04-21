"""Public snippet: reference tracking over legal chunks.

- Tracks internal / parent references with bounded hops.
- Prevents unbounded expansion while improving legal grounding.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Reference:
    ref_type: str  # internal | parent
    law_name: str
    article: str


@dataclass
class RefState:
    pending_refs: list[Reference] = field(default_factory=list)
    resolved_refs: list[Reference] = field(default_factory=list)
    all_context: list[dict] = field(default_factory=list)
    hop_count: int = 0
    max_hops: int = 3


def track_one_hop(state: RefState, get_article_fn, find_children_fn) -> RefState:
    if not state.pending_refs or state.hop_count >= state.max_hops:
        return state

    current = state.pending_refs.pop(0)
    docs: list[dict] = []

    if current.ref_type == "internal":
        law_id = "1823" if current.law_name == "건축법" else "2118"
        docs = get_article_fn(law_id=law_id, article_num=current.article)
    elif current.ref_type == "parent":
        docs = find_children_fn(law_name=current.law_name, article_num=current.article)

    if docs:
        state.all_context.extend(docs)
        state.resolved_refs.append(current)

    state.hop_count += 1
    return state
