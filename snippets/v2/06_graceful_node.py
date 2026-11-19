"""Public snippet (v2): 실패해도 답변하는 노드 래퍼 + 빠진 근거 안내 + 마지막 질문 "다시 확인".

문제  중간 단계(조례 검색 등)가 실패하면 v1은 아무 일 없던 것처럼 답했다 — 사용자는 근거가 빠진 줄 모른다.
방법  1) 모든 그래프 노드를 래퍼로 감싼다: 예산 초과·예외면 stop_reason을 세우고 이후 근거 단계는 건너뛴 채
         **답변 단계만 실행**(모은 근거로 마무리). 어떤 근거가 빠졌는지(gap)는 기록한다.
      2) 빠진 근거가 있으면 답변에 안내를 붙이고, **마지막 턴만** 다시 확인할 수 있게 한다 —
         턴 시작 전 메모리 스냅샷으로 되돌린 뒤 같은 질문을 재실행(실패한 답변은 대화 맥락에 남지 않음).
결과  사용자에게 "지역 조례를 확인하지 못했어요 — 다시 확인" 같은 안내가 나가고, 재시도해도 턴 수가 늘지 않는다.

실제 코드를 단순화한 개념 설명용 재구현입니다. 실행: python 06_graceful_node.py
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Callable

ALWAYS_RUN = {"answer"}
GAP_LABELS = {"local_ordinance": "지역 조례", "reference_expansion": "참조 조문", "evidence_stopped": "근거 보강"}


@dataclass
class Trace:
    gaps: list[str] = field(default_factory=list)


def node(name: str, gap_on_error: str = "evidence_stopped"):
    def deco(fn: Callable[[dict, Trace], dict]):
        def wrapper(state: dict, trace: Trace) -> dict:
            if state.get("stop_reason") and name not in ALWAYS_RUN:
                return {}  # 앞에서 멈췄으면 근거 단계는 건너뛴다
            try:
                return fn(state, trace) or {}
            except Exception as e:  # noqa: BLE001 — 실패도 강등으로 처리하되 반드시 기록
                trace.gaps.append(gap_on_error)
                return {"stop_reason": f"error:{name}:{type(e).__name__}"}
        return wrapper
    return deco


@node("search_ordinance", gap_on_error="local_ordinance")
def search_ordinance(state: dict, trace: Trace) -> dict:
    if state.get("ordinance_down"):
        raise ConnectionError("vector db timeout")
    return {"evidence": state["evidence"] + ["가평군 건축 조례 제34조"]}


@node("answer")
def answer(state: dict, trace: Trace) -> dict:
    text = f"근거 {state['evidence']}로 답변합니다."
    missing = [GAP_LABELS[g] for g in trace.gaps]
    notice = f"확인하지 못한 근거: {', '.join(missing)} — '다시 확인'을 눌러 주세요." if missing else None
    return {"answer": text, "notice": notice}


def run_turn(memory: dict, query: str, *, ordinance_down: bool, retry: bool = False) -> dict:
    if retry:  # 마지막 턴만: 그 턴 직전 스냅샷으로 되돌리고 같은 질문으로
        query, memory = memory["last_turn"]["query"], copy.deepcopy(memory["last_turn"]["prev"])
    snapshot = copy.deepcopy(memory)
    trace, state = Trace(), {"evidence": ["건축법 제46조"], "ordinance_down": ordinance_down}
    for step in (search_ordinance, answer):
        state.update(step(state, trace))
    memory["dialogue"] += [query, state["answer"]]
    memory["last_turn"] = {"query": query, "prev": snapshot, "retryable": bool(trace.gaps)}
    return {"memory": memory, **state}


if __name__ == "__main__":
    mem = {"dialogue": ["A질문", "A답"], "last_turn": None}
    r1 = run_turn(mem, "가평군 건축선은?", ordinance_down=True)
    print(r1["answer"], "|", r1["notice"])
    r2 = run_turn(r1["memory"], "", ordinance_down=False, retry=True)
    print(r2["answer"], "|", r2["notice"])
    print("대화 맥락:", r2["memory"]["dialogue"])  # 실패한 첫 답변은 남지 않는다
