"""Public snippet (v3): 아키 · 테오 · 베리 — LangGraph 연결과 하네스 공유.

설계 요점
- 아키(질문 이해·답변)와 베리(근거 점검)만 LLM을 부르고, 테오(검색·보강)는 LLM 없이 **동시에** 실행한다.
  LLM은 서로의 결과가 필요해 순차로, 외부 검색은 독립적이라 병렬로 — 1차 검색 시간 −45%.
- 재점검은 **검색으로 새 근거가 들어왔을 때만**(최대 2회). 베리가 후보표에서 직접 고른 참조만 가져온 경우는
  재점검으로 바뀌는 게 없어 생략 — 평가에서 재점검 문항 31 → 18, 비용 +21% → +5%.
- 예산·재시도·강등·대화 메모리는 v2 하네스를 그대로 쓴다(05·06). 노드는 v2 래퍼로 감싸고 그래프만 바꿨다.
- LangGraph 주의점: v2 노드 래퍼의 타입 표기가 v2 상태라, `input_schema`를 v3 상태로 지정하지 않으면
  v3 전용 키(후보표 등)가 노드 입력에서 조용히 빠진다.

실제 코드를 단순화한 개념 설명용 재구현입니다(LLM·검색은 가짜 함수). 실행: pip install langgraph && python 11_v3_graph.py
"""

from __future__ import annotations

import contextvars
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, TypedDict

from langgraph.graph import END, START, StateGraph

MAX_BERI_ROUNDS = 2


class V3State(TypedDict, total=False):
    query: str
    queries: list[str]
    evidence: list[str]
    request: dict
    beri_round: int
    beri_done: bool
    gather_added: int
    gather_searched: bool
    answer: str


def parallel(fns: list[Callable[[], list[str]]], workers: int = 4) -> list[list[str]]:
    """테오: 독립적인 검색을 동시에(추적 문맥 유지). 외부 API 429를 막으려고 동시 실행 수는 제한."""
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return [f.result() for f in [pool.submit(contextvars.copy_context().run, fn) for fn in fns]]


def fake_search(q: str) -> list[str]:
    return {"바닥면적 산정": ["건축법 시행령 제119조"], "용도변경": ["건축법 제19조"]}.get(q, [])


def aki_understand(s: V3State) -> V3State:
    return {"queries": ["바닥면적 산정", "용도변경"]}


def teo_search(s: V3State) -> V3State:
    hits = parallel([lambda q=q: fake_search(q) for q in s["queries"]])
    return {"evidence": sorted({h for hs in hits for h in hs})}


def beri_check(s: V3State) -> V3State:
    rnd = s.get("beri_round", 0) + 1
    # 실제로는 경량 LLM이 후보표(10_beri_candidates.py)를 보고 고른다
    request = {"refs": ["건축법 제16조"], "queries": ["변경되는 바닥면적"]} if rnd == 1 else {}
    return {"beri_round": rnd, "request": request, "beri_done": not request}


def teo_gather(s: V3State) -> V3State:
    req = s["request"]
    searched = parallel([lambda q=q: ["건축법 시행령 제12조"] for q in req.get("queries", [])])
    new = [e for e in req.get("refs", []) + [h for hs in searched for h in hs] if e not in s["evidence"]]
    return {"evidence": s["evidence"] + new, "gather_added": len(new), "gather_searched": bool(req.get("queries"))}


def aki_answer(s: V3State) -> V3State:
    return {"answer": f"근거 {s['evidence']}로 답변 (베리 점검 {s['beri_round']}회)"}


def after_beri(s: V3State) -> str:
    return "answer" if s.get("beri_done") else "teo_gather"


def after_gather(s: V3State) -> str:
    recheck = s.get("gather_added", 0) > 0 and s.get("gather_searched") and s["beri_round"] < MAX_BERI_ROUNDS
    return "beri_check" if recheck else "answer"


def build():
    g = StateGraph(V3State)
    for name, fn in [("understand", aki_understand), ("initial_search", teo_search), ("beri_check", beri_check),
                     ("teo_gather", teo_gather), ("answer", aki_answer)]:
        g.add_node(name, fn, input_schema=V3State)  # 실제 코드에서는 v2 래퍼로 감싼 노드라 꼭 필요
    g.add_edge(START, "understand")
    g.add_edge("understand", "initial_search")
    g.add_edge("initial_search", "beri_check")
    g.add_conditional_edges("beri_check", after_beri, ["teo_gather", "answer"])
    g.add_conditional_edges("teo_gather", after_gather, ["beri_check", "answer"])
    g.add_edge("answer", END)
    return g.compile()


if __name__ == "__main__":
    print(build().invoke({"query": "각 층의 변경되는 바닥면적 산정 방법"})["answer"])
