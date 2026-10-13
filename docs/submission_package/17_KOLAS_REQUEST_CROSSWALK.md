# 한국인공지능검증원 요청사항 대응 위치표

- 문서 ID: `KOLAS-DOC-017`
- 버전: `0.1-review`
- 상태: `REVIEW`
- 기준일: `2026-10-13`
- 목적: 시험기관이 요청한 5개 대항목·19개 세부사항의 답변과 근거 위치를 한 번에 찾을 수 있게 한다.

상태 표기:

- `충족`: 현재 문서·코드·증적에서 직접 확인 가능
- `조건부 충족`: 현재 확인 가능하나 final 시험환경에서 재고정 필요
- `기관협의 필요`: 시험 결과의 의미/조건에 영향을 주어 시험 전 승인 필요
- `확인된 범위만 기재`: 사실은 확인되었으나 과거 세부기록을 추정하지 않음

| 번호 | 시험기관 요청 | 1차 확인 위치 | 상태 | 핵심 메모 |
|---|---|---|---|---|
| 1-1 | 서비스명, 시스템 버전, 위험요인 식별 기능 범위 | `02_SYSTEM_UNDER_TEST.md` 1·2·6절; `01_TEST_METHOD.md` 2절; `12_VERSION_MANIFEST.md` | 조건부 충족 | final release/tag 시험 직전 freeze |
| 1-2 | API 접근 방법 포함 시험 진행 과정 | `11_API_ACCESS_GUIDE.md`; `10_REPRODUCIBILITY_GUIDE.md`; `02_SYSTEM_UNDER_TEST.md` 3절 | 충족 | credential은 별도 보안채널 |
| 1-3 | SW/HW 환경 | `16_EXECUTION_ENVIRONMENT_REPEAT_POLICY.md` 2절; `02_SYSTEM_UNDER_TEST.md` 10절 | 조건부 충족 | 2026-10-13 audit host 기록; final endpoint 변경 시 재수집 |
| 2-1 | 425 scenario / 843 기준 위험요인 원본 및 고유 ID 연결표 | `04_GT_SPECIFICATION.md` 3~5·10·12절; `data/raw/kolas_v7_73_test.csv.bz2`; `scenarios_v1.jsonl`; `gt_lineage_index_v1.csv` | 충족 | evaluator exact processing source와 lineage 확보; legacy XLSX bytes는 별도 미확보 |
| 2-2 | 데이터 출처, 시나리오 선정기준, GT 작성·검토·버전 이력 | `04_GT_SPECIFICATION.md`; `05_GT_SOURCE_PROVENANCE.md`; `GT_CHANGELOG.md`; `14_CHANGE_CONTROL.md` | 확인된 범위만 기재 | GT는 연구실 구성원 검토 완료; 확인되지 않은 과거 검토 인원/통계는 창작하지 않음 |
| 2-3 | GT 적정성 근거(전문가 검토, 중복·누락 등) | `04_GT_SPECIFICATION.md` 7·11·13·15절; `05_GT_SOURCE_PROVENANCE.md` 14절 | 조건부 충족 | GT 연구실 검토 완료 사실 + 자동 completeness/duplicate audit. 상세 과거 검토기록은 보유 범위만 제출 |
| 2-4 | 학습 및 시험 데이터 간 중복 활용 여부 | `15_TEST_DATA_INDEPENDENCE_AUDIT.md`; `gt_ra_overlap_audit_20261013.json`; `sut_gt_source_overlap_audit_20261013.json` | **기관협의 필요** | SEEXR fine-tuning 경로는 확인되지 않았으나 runtime RA retrieval DB와 GT 사이 상당한 exact overlap 확인 |
| 3-1 | 시스템 원출력 위험요인 추출 필드와 처리 방법 | `01_TEST_METHOD.md` 3절; `src/kolas_llm_judge/parser.py` | 충족 | XML `./items/item` = 1 generated risk |
| 3-2 | 복합 문장을 개별 위험요인으로 분리하는 기준/예시 | `01_TEST_METHOD.md` 3절 | 충족 | semantic split 안 함; SUT XML item 경계를 평가단위로 사용 |
| 3-3 | 중복·포괄·메커니즘 생략 표현 처리 기준 | `01_TEST_METHOD.md` 5절; `prompts/judge_binary_v1.md`; `configs/rubric_binary_v1.yaml` | 충족 | 키워드만 같으면 MATCH 아님; 정보 부족 시 낙관적 true 금지 |
| 3-4 | 관련 코드 또는 도구 | `dataset.py`; `parser.py`; `binary_judge.py`; `binary_evaluation.py`; `identification.py` | 충족 | source identity/hash 별도 고정 |
| 4-1 | Judge 모델·버전·설정, 전체 프롬프트, 출력형식 | `08_EVALUATOR_SPECIFICATION.md` 2~4절; `prompts/judge_binary_v1.md`; `configs/rubric_binary_v1.yaml` | 충족 | prompt/rubric hash fixed |
| 4-2 | 사전 검증 문항, 기준 판정값, 작성·검토 근거 | `09_EVALUATOR_QUALIFICATION.md`; `ajqg_seed_v1.yaml`; `qualification_controls.py`; `ajqg_gate_v1.yaml`; AJQG evidence | 충족 | expected Boolean은 constructed controls로 명시 |
| 4-3 | 판정 오류·판정 불가 특이사항 처리 | `08_EVALUATOR_SPECIFICATION.md`; `09_EVALUATOR_QUALIFICATION.md`; `01_TEST_METHOD.md` 8~9절 | 충족 | completeness failure, bounded retry, requalification 규칙 |
| 5-1 | 전체 데이터셋 반복시험 횟수 | `01_TEST_METHOD.md` 11절; `LAB_METHOD_DECISION_REGISTER.md` DEC-METHOD-005/006 | 기관협의 필요 | 2회 권고; 반복횟수·허용변동 시험 전 freeze |
| 5-2 | 반복마다 시스템 결과 신규 생성 여부 | `16_EXECUTION_ENVIRONMENT_REPEAT_POLICY.md` 3~6절; `official_live.py`; `sut_client.py` | 충족 | fresh official run마다 새 RUN_ID/dir 및 신규 SUT 호출 |
| 5-3 | cache·session 초기화 및 동일 입력 적용 | `16_EXECUTION_ENVIRONMENT_REPEAT_POLICY.md` 4~9절; `sut_client.py`; `parallel_runner.py` | 충족(주의) | case별 신규 session, prior repeat checkpoint 미사용; provider input cache는 output reuse와 구분 |
| 5-4 | timeout 기준 및 retry 허용조건 | `01_TEST_METHOD.md` 9절; `11_API_ACCESS_GUIDE.md` 10~11절 | 충족 | SUT/Judge 180s, retry 3 등 |
| 5-5 | SUT 비응답 vs 시험 인프라 장애 구분 | `01_TEST_METHOD.md` 8절; `10_REPRODUCIBILITY_GUIDE.md` 7절 | 충족 | `sut_non_completion` / `evaluator_failure` / `infrastructure_failure` |

## 가장 중요한 시험 전 결정

`DEC-METHOD-010` / `BLK-LAB-010`:

- 현재 통합제품(RA retrieval DB 포함)의 end-to-end 성능으로 시험할 것인지
- 또는 independent holdout/leakage-controlled 조건을 별도로 구성할 것인지

시험 시작 전에 시험기관과 확정한다.

## HWP 반영

최종 HWP/HWPX에는 본 표를 **제출자료 개요 직후 “시험기관 요청사항 대응표”**로 배치한다. 이렇게 하면 시험기관 담당자가 이메일의 각 요청사항을 붙임 전체에서 다시 검색하지 않고 1차 근거 위치로 바로 이동할 수 있다.
