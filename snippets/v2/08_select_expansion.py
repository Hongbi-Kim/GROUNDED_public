"""Public snippet (v2): 참조 확장 상한 — "앞에서 N개 자르기" 대신 고르는 순서를 설계.

문제  참조 확장에 상한이 없어 한 질문에 조문이 최대 109개 붙었다(출처 80개가 뜨는 답변). 그렇다고 앞에서 20개만
      자르면 ① 맨 뒤에 붙는 별표가 먼저 잘리고 ② 수십 개를 인용하는 조문 하나가 자리를 독차지해서 **정답 조문까지
      잘렸다**(효과 절반 손실).
방법  1) 우선 통과: 정의 조항(유사도는 낮아도 자주 필요), 근거 조문 2개 이상이 함께 인용한 조문
      2) 나머지는 근거 조문(1차 검색 순위)마다 줄을 세워 **한 개씩 번갈아** 담기 — 줄 안에서는 본문이 직접 언급한 별표 먼저
      3) 근거 조문당 최대 k개, 전체 최대 N개. 상한값은 저장된 검색 결과로 **LLM 없이 시뮬레이션**해 정했다.
결과  같은 상한 20에서 예전 방식은 정답을 잃고(0.789) 이 방식은 지킴(0.816), 추가 조문 수 **−60%**(1,408 → 560).

실제 코드를 단순화한 개념 설명용 재구현입니다. 실행: python 08_select_expansion.py
"""

from __future__ import annotations


def select_expansion(rows: list[dict], source_rank: list[str], *, cap: int, per_source: int,
                     cite_count: dict[str, int]) -> list[dict]:
    rank = {s: i for i, s in enumerate(source_rank)}
    pinned = [r for r in rows if "정의" in r["title"] or cite_count.get(r["key"], 1) >= 2]
    pinned.sort(key=lambda r: ("정의" not in r["title"], rank.get(r["src"], 99)))
    pinned_keys = {r["key"] for r in pinned}

    queues: dict[str, list[dict]] = {}
    for r in rows:
        if r["key"] not in pinned_keys:
            queues.setdefault(r["src"], []).append(r)
    for src, q in queues.items():
        q.sort(key=lambda r: not r.get("appendix"))  # 안정 정렬: 별표 먼저, 나머지는 인용 순서 유지
        queues[src] = q[:per_source]

    order = sorted(queues, key=lambda s: rank.get(s, 99))
    interleaved, depth = [], 0
    while any(depth < len(queues[s]) for s in order):
        interleaved += [queues[s][depth] for s in order if depth < len(queues[s])]
        depth += 1
    return (pinned + interleaved)[:cap]


if __name__ == "__main__":
    # 시행령 제119조가 30개를 인용하고, 정답(건축법 제16조)은 다른 근거(건축법 제19조)가 인용한 경우
    rows = [{"key": f"시행령 {n}조", "title": "", "src": "시행령 제119조"} for n in range(1, 31)]
    rows += [{"key": "건축법 제16조", "title": "허가와 신고사항의 변경", "src": "건축법 제19조"},
             {"key": "건축법 제2조", "title": "정의", "src": "시행령 제119조"},
             {"key": "별표 1", "title": "용도별 건축물의 종류", "src": "건축법 제19조", "appendix": True}]
    naive = [r["key"] for r in rows[:6]]
    smart = [r["key"] for r in select_expansion(rows, ["시행령 제119조", "건축법 제19조"], cap=6, per_source=8,
                                                 cite_count={})]
    print("앞에서 자르기:", naive, "→ 정답 포함?", "건축법 제16조" in naive)
    print("고르는 순서  :", smart, "→ 정답 포함?", "건축법 제16조" in smart)
