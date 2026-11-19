"""Public snippet (v2): 인용 번호가 없을 때 — "근거 전부"가 아니라 답변 본문의 조문 표기로 인용을 추정.

문제  답변 모델이 어떤 근거를 썼는지(인용 번호)를 돌려주지 않으면, 예전엔 넘긴 근거 **전부**를 출처로 표시했다
      → 출처 80개가 뜨는 답변, 인용 정밀도 0.01.
방법  답변 본문의 "건축법 제44조", "같은 법 시행령 제80조의2", "별표 3"을 근거 목록과 맞춘다.
      애매하면 고르지 않는다: 같은 번호가 여러 법령에 있으면 바로 앞의 법령명으로만 고르고, 근거에 없는 법령명이
      앞에 있으면("민법 제19조") 다른 법령의 제19조로 잘못 잡지 않는다. 그래도 못 찾으면 상위 5개만.
결과  저장된 답변 81건에서 모델이 준 인용과 비교해 **정밀도 0.95 / 재현율 0.99**, 출처 최대 80 → 20개.

실제 코드를 단순화한 개념 설명용 재구현입니다. 실행: python 09_citation_inference.py
"""

from __future__ import annotations

import re

MENTION = re.compile(r"제\s*(\d+)\s*조(?:\s*의\s*(\d+))?")
OTHER_LAW = re.compile(r"[가-힣]+(법|령|규칙|조례)$")
SAME_LAW = re.compile(r"(?:같은법|동법)(시행령|시행규칙)?$")


def infer_used(answer: str, refs: list[dict], top_n: int = 5) -> tuple[list[str], str]:
    """→ (인용으로 볼 근거 key들, 출처: inferred_from_text | top_n)."""
    norm = lambda s: re.sub(r"[\s「」·]", "", s)  # noqa: E731
    names = {norm(r["law"]) for r in refs}
    by_label: dict[str, list[dict]] = {}
    for r in refs:
        by_label.setdefault(r["label"], []).append(r)

    picked, last_law, prev_end = [], None, 0
    for m in MENTION.finditer(answer):
        window = norm(answer[max(prev_end, m.start() - 40): m.start()])
        prev_end = m.end()
        found = [n for n in names if n in window]
        law = max(found, key=lambda n: (window.rfind(n) + len(n), len(n))) if found else None
        if law is None and last_law and (same := SAME_LAW.search(window)):
            law = re.sub(r"(시행령|시행규칙)$", "", last_law) + (same.group(1) or "")  # "같은 법 시행령"
        other = law is None and bool(OTHER_LAW.search(window))  # 근거에 없는 법령명이 바로 앞
        last_law = law or (last_law if re.fullmatch(r"(및|,|와|과)*", window) else None)  # "제44조 및 제45조"
        label = f"제{m.group(1)}조" + (f"의{m.group(2)}" if m.group(2) else "")
        cands = by_label.get(label, [])
        target = law or last_law
        hit = [c for c in cands if target and norm(c["law"]) == target] or (cands if len(cands) == 1 and not other else [])
        if len(hit) == 1 and hit[0]["key"] not in picked:
            picked.append(hit[0]["key"])
    return (picked, "inferred_from_text") if picked else ([r["key"] for r in refs][:top_n], "top_n")


if __name__ == "__main__":
    refs = [{"key": k, "law": l, "label": lb} for k, l, lb in [
        ("A", "건축법", "제44조"), ("B", "건축법", "제2조"), ("C", "건축법 시행령", "제2조"),
        ("D", "건축법 시행령", "제80조의2"), ("E", "주차장법", "제19조")]]
    for text in ["건축법 제44조 및 제2조에 따라", "건축법 제44조, 같은 법 시행령 제80조의2에 따라",
                 "「건축법 시행령」 제2조의 정의", "민법 제19조에 따르면",  # 주차장법 제19조(E)로 잡지 않음
                 "조문 언급 없음"]:
        print(f"{text:<32} → {infer_used(text, refs, top_n=2)}")
