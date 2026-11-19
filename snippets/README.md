# Public Code Snippets

비공개 저장소 전체 대신, 버전별로 **문제를 푼 핵심 로직만** 단순화해 재구현한 코드입니다(실제 프로덕션 코드 그대로가 아닌 개념 설명용).
각 파일 맨 위에 **문제 / 방법 / 결과(지표)** 를 적었고, 대부분 외부 서비스 없이 바로 실행됩니다(`python <파일>`).

| 버전 | 파일 | 무엇을 보여주나 | 결과 |
|---|---|---|---|
| v1 | [01_condition_slot_parser.py](v1/01_condition_slot_parser.py) | 질문에서 지역·용도·공사유형 조건 추출 | — |
| v1 | [02_target_retrieval.py](v1/02_target_retrieval.py) | 쟁점별 검색 + 필터 | — |
| v1 | [03_reference_tracker.py](v1/03_reference_tracker.py) | 참조 조문 추적 — **법령 2개만 아는 표**(v1의 한계, v2와 비교용) | 연결 비율 3.9% |
| v1 | [04_appendix_lookup.py](v1/04_appendix_lookup.py) | "별표 N" 언급으로 별표 조회 | — |
| v2 | [05_budget_and_retry.py](v2/05_budget_and_retry.py) | 턴 예산 사전 차단·정산, 실패 상태 분류, 429 백오프, 대체값 기록 | 실패를 숨기지 않고 관측(오류·대체 0건 확인) |
| v2 | [06_graceful_node.py](v2/06_graceful_node.py) | 실패해도 답변하는 노드 래퍼 + 빠진 근거 안내 + 마지막 질문만 "다시 확인" | 재확인해도 실패한 답변이 맥락에 남지 않음 |
| v2 | [07_law_resolver.py](v2/07_law_resolver.py) | "영"·"법"·정식 명칭·약칭 → 조문 주소(LLM 없음), 못 푼 참조는 사유와 함께 | 연결 비율 **3.9% → 97.9%** (23,907건) |
| v2 | [08_select_expansion.py](v2/08_select_expansion.py) | 참조 확장 상한: 정의·공통 인용 우선 + 근거별 번갈아 + 조문당 상한 | 정답 유지하며 추가 조문 **−60%** |
| v2 | [09_citation_inference.py](v2/09_citation_inference.py) | 인용 번호 누락 시 답변 본문의 조문 표기로 인용 추정 | 정밀도 0.95 / 재현율 0.99, 출처 80 → 20개 |
| v3 | [10_beri_candidates.py](v3/10_beri_candidates.py) | 검증 에이전트에게 주는 **제목 붙은 참조 후보표** + 번호로 고르는 출력 형식 | 참조 판단 정확도 **16% → 68~81%** |
| v3 | [11_v3_graph.py](v3/11_v3_graph.py) | 아키·테오·베리 LangGraph 연결: 동시 검색 → 점검 → 보강 → 조건부 재점검 | 1차 검색 **−45%**, 비용 +5% |

실행 요구사항: 대부분 표준 라이브러리만. `10`은 `pydantic`, `11`은 `langgraph`.
수치의 측정 방법과 한계는 저장소 README의 [Agent Evolution](../README.md#agent-evolution--v1--v2--v3) 참고.
