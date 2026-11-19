"""Public snippet (v2): 법령 간 참조 연결기 — LLM 없이 "영 제80조의2"를 실제 조문 주소로.

문제  조문에 적힌 참조는 「국토계획법」 제77조 같은 정식 명칭도 있지만, "영"·"법"·"국토교통부령"처럼 **참조가
      들어 있는 법령을 기준으로 해야** 뜻이 정해지는 줄임 표현이 많다. v1은 건축법·시행령 2개만 아는 표로
      변환해서 나머지는 버렸다(../v1/03_reference_tracker.py).
방법  법령 목록(법령 5,596 + 자치법규 13,514)을 이름 정규화(공백·낫표·가운뎃점 무시)로 색인하고, 순서대로 푼다:
      1) 상대 참조 — "법"/"영"/"부령"을 **참조가 있는 법령의 법령군**(건축법 · 건축법 시행령 · 건축법 시행규칙)에서
      2) 정식 명칭 일치  3) 약칭  4) 같은 이름의 자치법규가 여럿이면 같은 지자체.
      못 푼 참조는 버리지 않고 **사유와 함께** 남긴다(조문 번호 없음, DB에 없는 법령, 개정 전 법령 …).
결과  조문 번호가 있는 외부 참조 23,907건 중 연결 비율 **3.9% → 97.9%**, 연결된 조문의 99.8%가 실제 검색 DB에 존재.

실제 코드를 단순화한 개념 설명용 재구현입니다. 실행: python 07_law_resolver.py
"""

from __future__ import annotations

import re
from dataclasses import dataclass

SAME_LAW, DECREE, RULE = {"법"}, {"영", "대통령령", "시행령"}, {"시행규칙", "국토교통부령"}


def norm(name: str) -> str:
    return re.sub(r"[\s「」·ㆍ]", "", name or "")


@dataclass(frozen=True)
class Law:
    law_id: str
    name: str
    is_statute: bool  # 법률인가(하위 법령이 아닌가)


class LawResolver:
    def __init__(self, laws: list[Law], aliases: dict[str, str]):
        self.by_name = {norm(l.name): l for l in laws}
        self.aliases = {norm(a): norm(c) for a, c in aliases.items()}

    @staticmethod
    def family(name: str) -> str:  # "건축법 시행령" → "건축법"
        n = norm(name)
        return next((n[: -len(s)] for s in ("시행규칙", "시행령") if n.endswith(s)), n)

    def resolve(self, ref_name: str, article: str, source: Law) -> tuple[str | None, str]:
        """→ (조문 주소 "법령ID:조:가지", 방법) 또는 (None, 못 푼 사유)."""
        if not article:
            return None, "no_article"
        m = re.fullmatch(r"(\d+)(?:의(\d+))?", article)
        if not m:
            return None, "bad_article"
        n = norm(ref_name)
        if n.startswith("구") and n[1:] in self.by_name:
            return None, "old_version"  # "구 건축법" — 현재 조문과 다르다
        rel = "" if n in SAME_LAW else "시행령" if n in DECREE else "시행규칙" if n in RULE else None
        if rel is not None:
            base = self.family(source.name)
            if rel == "" and base == norm(source.name) and not source.is_statute:
                return None, "relative_target_missing"  # 이름에 시행령/규칙이 없는 하위 법령 안의 "법"
            target, how = self.by_name.get(base + rel), "relative"
        else:
            target, how = self.by_name.get(n), "exact"
            if target is None and n in self.aliases:
                target, how = self.by_name.get(self.aliases[n]), "alias"
        if target is None:
            return None, "unknown_law" if rel is None else "relative_target_missing"
        return f"{target.law_id}:{m.group(1)}:{m.group(2) or '0'}", how


if __name__ == "__main__":
    laws = [
        Law("001823", "건축법", True), Law("002118", "건축법 시행령", False), Law("006191", "건축법 시행규칙", False),
        Law("009294", "국토의 계획 및 이용에 관한 법률", True), Law("011111", "가평군 건축 조례", False),
    ]
    r = LawResolver(laws, aliases={"국토계획법": "국토의 계획 및 이용에 관한 법률"})
    src_ord, src_decree = laws[4], laws[1]
    cases = [
        ("건축법", "58", src_ord),          # 정식 명칭
        ("영", "80의2", laws[0]),           # 건축법 안의 "영" → 건축법 시행령
        ("법", "44", src_decree),           # 시행령 안의 "법" → 건축법
        ("국토교통부령", "12", laws[0]),     # → 건축법 시행규칙
        ("국토계획법", "77", src_ord),      # 약칭
        ("대통령령", "", laws[0]),          # 조문 번호 없음 → 원래 특정 불가
        ("구 건축법", "69", src_ord),       # 개정 전 법령
        ("특허협력조약", "3", laws[0]),      # DB에 없는 법령
    ]
    for name, art, src in cases:
        a, _, sub = art.partition("의")
        shown = f"{name} 제{a}조" + (f"의{sub}" if sub else "") if art else f"{name}으로 정하는 기준"
        print(f"[{src.name}] {shown:<20} → {r.resolve(name, art, src)}")
