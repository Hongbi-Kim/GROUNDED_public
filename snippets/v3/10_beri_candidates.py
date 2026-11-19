"""Public snippet (v3): 검증 에이전트 '베리'에게 주는 참조 후보표 — 판단 모델 대신 판단 정보를 바꾼다.

문제  v1·v2의 근거 판단 LLM은 참조를 `{"law_name": "영", "article": "80의2"}` 목록으로만 보고 "확장할까?"를 예/아니오로
      정했다. 그 조문이 무엇인지 모르니 보수적으로 "불필요"를 골랐다 — 참조가 필요한 문항의 84%에서 놓침.
방법  코드가 먼저 1차 근거가 인용하는 조문을 (v2 연결기로) 풀어 **미리 조회**하고, 제목을 붙인 후보표(R1, R2, …)를 만든다.
      베리는 예/아니오 대신 **필요한 후보를 번호로** 고른다(fetch_refs). 고른 조문은 이미 조회한 것을 그대로 넣는다.
      구현 전에 천장부터 확인: v2가 놓친 정답 조문 6개가 모두 후보표 상위 13위 안 → 고르기만 잘하면 강제 확장과 같은 효과.
결과  참조 판단 정확도 **16% → 68~81%**, 확장 기여(Evidence − Node Recall) +0.013 → +0.044. LLM 호출 수는 v2와 비슷.

실제 코드를 단순화한 개념 설명용 재구현입니다. 실행: python 10_beri_candidates.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field  # pip install pydantic


@dataclass
class Candidate:
    label: str
    law: str
    section: str
    title: str
    cited_by: str
    cite_count: int = 1
    row: dict = field(default_factory=dict, repr=False)  # 이미 조회한 조문 — 고르면 그대로 근거에 추가

    def line(self) -> str:
        tags = (["정의"] if "정의" in self.title else []) + ([f"근거 {self.cite_count}개가 인용"] if self.cite_count > 1 else [])
        tag = f" [{', '.join(tags)}]" if tags else ""
        return f"{self.label}: {self.law} {self.section} 「{self.title}」{tag} ← {self.cited_by}"


def build_candidate_table(resolved: list[dict], limit: int = 30) -> list[Candidate]:
    """resolved: 연결기로 푼 뒤 조회까지 끝난 참조(정렬은 08_select_expansion과 같은 순서라고 가정)."""
    return [Candidate(f"R{i}", r["law"], r["section"], r["title"], r["cited_by"], r.get("cite_count", 1), r)
            for i, r in enumerate(resolved[:limit], 1)]


class IssueCheck(BaseModel):
    issue: str
    status: Literal["covered", "weak", "missing"]


class BeriCheck(BaseModel):
    """베리의 출력 — v2의 needs_reference_expansion(bool) 자리에 '무엇을'이 들어간다."""
    issues: list[IssueCheck]
    fetch_refs: list[str] = Field(description='가져올 후보 번호, 예: ["R2", "R5"]. 질문의 요건·절차·예외·용어와 관련된 것만')
    needs_local_regulation: bool = False
    additional_search_queries: list[str] = Field(default_factory=list, max_length=3)
    done: bool = True


def apply(check: BeriCheck, table: list[Candidate], already: set[str]) -> list[dict]:
    by_label = {c.label: c for c in table}
    return [by_label[l].row for l in check.fetch_refs if l in by_label and by_label[l].row["key"] not in already]


if __name__ == "__main__":
    resolved = [
        {"key": "009087:2:0", "law": "전통사찰법", "section": "제2조", "title": "정의", "cited_by": "건축법 시행령 제119조"},
        {"key": "001823:55:0", "law": "건축법", "section": "제55조", "title": "건축물의 건폐율", "cited_by": "건축법 시행령 제119조"},
        {"key": "001823:16:0", "law": "건축법", "section": "제16조", "title": "허가와 신고사항의 변경",
         "cited_by": "건축법 제19조", "cite_count": 2},
    ]
    table = build_candidate_table(resolved)
    print("질문: 「건축법 시행령」 제12조제3항제2호에 따른 각 층의 변경되는 바닥면적 산정 방법\n")
    print("\n".join(c.line() for c in table))
    # 실제로는 LLM(경량 모델)이 위 표 + 근거 발췌를 보고 아래 형식으로 답한다
    check = BeriCheck(issues=[IssueCheck(issue="변경되는 바닥면적 산정", status="weak")], fetch_refs=["R3"], done=False)
    print("\n베리 선택:", check.fetch_refs, "→ 추가 근거:", [r["key"] for r in apply(check, table, already=set())])
