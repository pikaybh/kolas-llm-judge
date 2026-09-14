# SEEXR KOLAS 대응 구현 계획 및 이행 상태 v1

## 목적

한국인공지능검증원 회신에서 요구한 다음 세 조건을 시험 시스템 자체가 강제하도록 한다.

1. 시험방법과 판정기준을 시험 전에 정의하고 동결한다.
2. 시험결과의 유효성, 재현성, 객관성을 검증 가능한 방식으로 확보한다.
3. 입력부터 최종 결과까지 시험기록으로 역추적할 수 있게 한다.

본 문서는 `/home/pikaybh/Sandbox/kolas-llm-judge`의 실제 구현과 1:1로 대응하는 이행표다. 운영 에이전트 내부의 `riskRubricScorer`는 빈도·강도 산술/직관성 점검용이므로 본 KOLAS 성능시험의 판정기로 사용하지 않는다.

## 15단계 이행 계획

| 단계 | 구현 내용 | 상태 | 구현/증빙 |
|---|---|---|---|
| 1 | 시험 대상·절차 `KOLAS_RA_TEST_v1` 명문화 | 구현 | `docs/testing_lab_method_and_rubric_v1.md`, `docs/automated_kolas_protocol_v1.md` |
| 2 | GT schema 및 dataset versioning | 구현 | `KOLAS_RA_GT` v1.0.0, 425 scenarios/843 references, SHA-256 manifest |
| 3 | 사전 정의 Boolean Rubric | 구현 | `configs/rubric_binary_v1.yaml` |
| 4 | 독립 semantic Judge | 구현 | `binary-checklist-v1`, structured output, GPT-5.6 Sol frozen runtime |
| 5 | deterministic matching/metric layer | 구현 | mechanism+context KOLAS primary, Hungarian 1:1 diagnostic, 산술/범위 검증 |
| 6 | 공식 시험 Run 단위 관리 | 구현(독립 harness 방식) | Mastra Experiment DB에 결합하지 않고 Core API를 SUT로 호출하여 evaluator 독립성 유지. 각 run/case별 Core session/run id와 raw event를 기록 |
| 7 | manifest/hash/trace 보존 | 구현 | source fingerprint, config/prompt/rubric/data hashes, case artifacts, run seal |
| 8 | 반복 live inference 재현성 측정 | 구현 | `compare-repeatability`로 동일 frozen identity의 sealed run 2개 이상 비교 |
| 9 | Human–LLM validation | 구현/선택적 사전 검증 | human calibration CSV, Cohen's kappa/agreement gate, Judge repeatability. Concord는 별도 blinded expert review 도구로 유지 가능 |
| 10 | 소규모 pilot | 수행 이력 있음 | 기존 50-case development live run. 새 protocol 변경 후에는 새 pilot을 다시 수행해야 함 |
| 11 | 판정 threshold 확정 | 시험기관 협의 대기 | 절차 유효성 gate만 동결. SUT 성능 합격선은 `report_only_until_testing_lab_approval`로 강제 |
| 12 | 시험방법·Rubric 송부자료 | 구현 | `docs/testing_lab_method_and_rubric_v1.md` |
| 13 | 시험기관 피드백 반영 및 v1.0 최종 동결 | 외부 회신 대기 | 피드백 전 성능 threshold를 임의 확정하지 않음 |
| 14 | 공식 release/final 425-case run | 외부 합의 후 수행 | 현재는 official runner·preflight·seal까지 구현. 최종 시험은 합의 후 release tag에서 수행 |
| 15 | 강성대 연구원 회신 이메일 초안 | 구현 | `docs/email_draft_to_kang_sungdae.md` |

## 핵심 설계 결정

### KOLAS primary와 기존 KPI를 분리한다

KOLAS 주 지표는 다음의 **엄격한 의미적 식별 규칙**을 사용한다.

`same_hazard_mechanism AND context_compatible`

따라서 사고분류가 같아도 위험 메커니즘 또는 작업/노출 맥락이 다르면 정답으로 처리하지 않는다. 이 규칙의 reference-level many-to-one Recall을 `hazard_semantic_identification_recall`로 보고한다.

기존 수행계획/KPI 연속성을 위한 `hazard_identification_accuracy`는 보조지표로 보존한다. 이 지표는 사고유형 호환성을 독립 경로로 인정하기 때문에 KOLAS primary보다 넓다. 두 지표를 혼용하지 않는다.

### Judge 판단과 수치 계산을 분리한다

LLM Judge는 사전에 정의된 Boolean 항목만 판정한다. 매칭, 분모/분자 집계, Recall 및 기타 비율, 위험도 곱셈·범위 검사는 Python deterministic layer가 수행한다.

### 시험절차 유효성과 제품 성능 합격을 분리한다

현재 동결 가능한 것은 시험 **절차의 유효성**이다. AJQG 통과, 전체 case 처리, 시험 중 SUT source 불변, evaluator/infrastructure failure 0건, SHA-256 seal 검증을 요구한다.

제품 성능의 최종 합격선(예: Recall 0.90 이상)은 시험기관과 시험방법을 합의하기 전에 임의 확정하지 않는다. 현재 runtime은 이를 `report_only_until_testing_lab_approval`로 명시하고, threshold가 사전 승인 없이 동결되는 것을 validation 단계에서 거부한다.

## 완료 조건

외부 피드백 전 내부 구현 완료 조건은 다음과 같다.

- 전체 unit/integration test 통과
- 동결 dataset 재생성 시 scenarios SHA-256 불변
- official preflight 통과
- 새 protocol로 development live smoke/pilot 통과
- 각 run의 SHA-256 seal 검증 통과
- 동일 frozen identity의 반복 run에 대한 repeatability 산출 가능
- 시험방법/Rubric 문서와 실제 코드의 primary rule, Judge, SUT 설정, version/hash가 일치

시험기관 피드백 이후에는 승인된 성능 판정기준을 runtime에 추가하고 release tag를 생성한 뒤 425-case official run을 수행한다.
