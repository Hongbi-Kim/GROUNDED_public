"""Public snippet (v2): 턴 예산 + 실패 분류 + 재시도 — 에이전트 하네스의 바닥.

문제  v1은 외부 API가 실패하면 기본값으로 넘어가서(429 → "참조 불필요") 품질 저하가 보이지 않았고,
      요청당 비용·호출 상한이 없었다.
방법  모든 LLM·검색 호출을 한 실행기로 통과시킨다: 호출 **전** 예상 비용으로 예산 사전 차단 → 실행 →
      결과를 success / empty / rate_limited / timeout / failed로 분류 → 429는 전용 백오프로 재시도 →
      끝내 실패하면 정해진 대체값을 쓰되 **기록**한다(숨기지 않음).
결과  45문항 평가에서 오류·대체 0건을 실제로 관측할 수 있게 됨(v1은 측정 불가).

실제 코드를 단순화한 개념 설명용 재구현입니다. 실행: python 05_budget_and_retry.py
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable


class BudgetExceeded(Exception):
    pass


class RateLimited(Exception):
    pass


@dataclass
class Budget:
    max_cost_usd: float
    max_calls: int
    spent: float = 0.0
    calls: int = 0

    def check(self, est_cost: float) -> None:  # 호출 전: 최악 비용으로 사전 차단
        if self.calls + 1 > self.max_calls:
            raise BudgetExceeded("max_calls")
        if self.spent + est_cost > self.max_cost_usd:
            raise BudgetExceeded(f"cost {self.spent:.4f}+{est_cost:.4f} > {self.max_cost_usd}")

    def settle(self, actual_cost: float) -> None:  # 호출 후: 실제 사용량으로 정산
        self.calls += 1
        self.spent += actual_cost


@dataclass
class CallRecord:
    name: str
    status: str  # success | empty | rate_limited | timeout | failed
    retries: int
    fallback_used: bool


@dataclass
class Executor:
    budget: Budget
    records: list[CallRecord] = field(default_factory=list)
    rate_limit_retries: int = 3
    backoff_s: float = 0.01  # 데모용(실제는 5s → 10s → 20s, 상한 30s)

    def call(self, name: str, fn: Callable[[], Any], *, est_cost: float, fallback: Any = None) -> Any:
        self.budget.check(est_cost)  # BudgetExceeded는 위로 올라가 그래프가 "강등"으로 처리(06 참고)
        retries = 0
        while True:
            try:
                out = fn()
                self.budget.settle(est_cost)
                self.records.append(CallRecord(name, "success" if out else "empty", retries, False))
                return out
            except RateLimited:
                if retries >= self.rate_limit_retries:
                    status = "rate_limited"
                    break
                time.sleep(self.backoff_s * 2**retries)
                retries += 1
            except TimeoutError:
                status = "timeout"
                break
            except Exception:  # noqa: BLE001
                status = "failed"
                break
        self.records.append(CallRecord(name, status, retries, True))  # 대체값을 썼다는 사실을 남긴다
        return fallback


if __name__ == "__main__":
    ex = Executor(Budget(max_cost_usd=0.05, max_calls=10))
    flaky = iter([RateLimited(), RateLimited(), ["건축법 제44조"]])

    def search():
        item = next(flaky)
        if isinstance(item, Exception):
            raise item
        return item

    print(ex.call("dense_search", search, est_cost=0.0001, fallback=[]))
    print(ex.call("rerank", lambda: (_ for _ in ()).throw(TimeoutError()), est_cost=0.0001, fallback=None))
    for r in ex.records:
        print(r)
    try:
        ex.call("answer", lambda: "…", est_cost=0.06)
    except BudgetExceeded as e:
        print("budget stop:", e)
