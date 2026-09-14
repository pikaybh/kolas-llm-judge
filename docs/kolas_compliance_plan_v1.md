# SEEXR KOLAS 대응 구현 계획 및 이행 상태 v1

## 목적

시험기관 협의 전에 다음 세 조건을 기술적으로 검증 가능한 상태로 만든다.

1. 시험방법과 판정기준을 시험 전에 정의하고 동결할 수 있어야 한다.
2. 시험결과의 유효성, 재현성, 객관성을 별도 증빙으로 확인할 수 있어야 한다.
3. 입력부터 최종 aggregate까지 역추적 가능한 시험기록을 보존해야 한다.

본 문서는 `/home/pikaybh/Sandbox/kolas-llm-judge`의 실제 구현과 대응한다. 운영 에이전트 내부 `riskRubricScorer`는 본 KOLAS 성능시험 판정기로 사용하지 않는다.

## 15단계 이행 계획

| 단계 | 구현 내용 | 현재 상태 | 구현/증빙 |
|---|---|---|---|
| 1 | 시험 대상·절차 `KOLAS_RA_TEST_v1` 명문화 | 완료 | `docs/testing_lab_method_and_rubric_v1.md`, `docs/automated_kolas_protocol_v1.md` |
| 2 | GT schema 및 dataset versioning | 완료 | `KOLAS_RA_GT` v1.0.0, 425 scenarios / 843 references, raw+scenario SHA-256 |
| 3 | 사전 정의 Boolean Rubric | 완료 | `configs/rubric_binary_v1.yaml` |
| 4 | 독립 semantic Judge | 완료 | `binary-checklist-v1`, GPT-5.6 Sol, structured Boolean output |
| 5 | deterministic matching/metric layer | 완료 | KOLAS primary=`mechanism AND context`, supplementary KPI 별도, 산술/범위 검증 |
| 6 | 공식 시험 run 단위 관리 | 완료 | Core API SUT 호출, case별 session/run id 및 단계별 artifact |
| 7 | manifest/hash/trace 보존 | 완료 | evaluator/dataset/prompt/rubric/SUT fingerprints, SHA-256 run seal/verify |
| 8 | 반복 live inference 재현성 측정 | 완료 | `compare-repeatability`: sealed run identity 검증, aggregate/case/reference 안정성 |
| 9 | Human–LLM 독립 검증 경로 | 구현 완료, 전문가 라벨링은 별도 수행 | official Boolean 차원 그대로 blinded 2-rater CSV 생성/채점, Cohen's κ/agreement, source-run seal+sample identity binding. Official live의 필수 gate는 AJQG이며 human calibration은 시험 전 독립 meta-validation 용도 |
| 10 | 새 protocol 소규모 live pilot | 완료 | 1-case×2 smoke, 10-case×2 repeat pilot, AJQG 포함 10-case integrated pilot |
| 11 | 제품 성능 판정정책 사전 상태 고정 | 완료(숫자 합격선은 시험기관 협의 대상) | `report_only_until_testing_lab_approval`, 승인 전 `performance_thresholds_frozen=false` 강제 |
| 12 | 시험방법·Rubric 송부자료 | 완료 | `docs/testing_lab_method_and_rubric_v1.md` |
| 13 | 시험기관 피드백 수용 가능한 freeze 구조 | 완료 | runtime validator가 dataset/Judge/AJQG/SUT/metric policy를 검증. 피드백 수신 후 version bump 및 새 hash freeze 가능 |
| 14 | release candidate 검증 경로 | 구현 완료, 최종 425-case accredited run은 외부 합의 후 수행 | clean evaluator commit → official doctor → live dry-run/smoke → seal verification. 공식 425-case는 승인된 threshold/release에서 수행 |
| 15 | 강성대 연구원 이메일 초안 | 완료 | 1~14 내부 구현·검증 완료 후 `docs/email_draft_to_kang_sungdae.md` 최종 갱신 |

## 공식 경로와 전문가 검증 경로의 역할 분리

### Official live 필수 gate

시험 당일 공식 자동 경로는 다음을 강제한다.

`preflight → AJQG → live SUT inference → Boolean Judge → deterministic metrics → source recheck → report → run seal → verify`

AJQG는 104개 고정 control을 반복 평가하여 structured completion, semantic positive/negative, accident, mitigation, legal, critical safety, robustness 및 repeated-decision stability를 검사한다. AJQG 실패 시 공식 run은 진행하지 않는다.

### Human–LLM validation

Human–LLM validation은 시험 당일 case-by-case 수동 판정에 의존하지 않도록 **공식 run 밖의 사전 독립 검증**으로 분리한다.

- source sealed run을 읽기 전용으로 사용한다.
- `derived/binary_calibration/<run_id>/`에 blinded 표본을 만든다.
- 두 안전전문가는 Judge 결과를 보지 않고 동일 Boolean 차원을 독립 평가한다.
- 불일치는 `adjudicated_*`로 합의한다.
- Judge–Human agreement와 Cohen's κ를 계산한다.
- source run manifest SHA-256, run seal root SHA-256, CSV의 비라벨 sample identity SHA-256을 gate에 바인딩한다.
- calibration artifact를 sealed source run 내부에 추가하지 않는다.

구형 0–4/0–2 ordinal calibration은 연구/FACE 호환 경로로만 유지한다.

## 핵심 설계 결정

### KOLAS primary와 기존 KPI 분리

KOLAS 주 지표는 다음의 엄격한 의미적 식별 규칙을 사용한다.

`same_hazard_mechanism AND context_compatible`

사고분류가 같아도 위험 메커니즘이나 작업·노출 맥락이 다르면 primary 정답이 아니다. 이 reference-level many-to-one Recall을 `hazard_semantic_identification_recall`로 보고한다.

기존 사업 KPI 연속성을 위한 `hazard_identification_accuracy`는 supplementary로만 유지한다. 이 지표는 `accident_compatible`을 독립 성공 경로로 인정하므로 KOLAS primary보다 넓다.

### Judge 판단과 수치 계산 분리

LLM Judge는 사전 정의 Boolean만 판정한다. 최종 numerator/denominator, Recall, Hungarian 진단 매칭, 위험도 산술/범위 검사는 deterministic Python layer가 수행한다.

### 절차 유효성과 제품 성능 합격 분리

절차 유효성은 AJQG, 전체 case 처리, evaluator/infrastructure failure, SUT source stability, run seal 검증 등으로 판정한다.

제품 성능의 최종 숫자 합격선은 시험기관 협의 전 임의로 확정하지 않는다. 현재 runtime은 `sut_performance_decision=report_only_until_testing_lab_approval`을 강제한다.

## 현재 내부 검증 증빙

- AJQG: 104 controls × 2회, 376/376 반복 Boolean 결정 동일, gate PASS
- 1-case live smoke 2회: procedure valid, seal verified
- 10-case integrated pilot: 10/10 SUT 완료, evaluator/infrastructure failure 0, source stable, seal verified
- 동일 10-case 반복 run strict primary: 17/21(0.8095) 및 16/21(0.7619)
- 두 run primary 평균 0.7857, 표준편차 0.0238, range 0.0476
- 21 references 중 20개 탐지 여부 동일(95.24%), 1개 변동
- 같은 두 run의 넓은 supplementary KPI는 모두 21/21(1.0)으로, strict primary가 실제 의미적 변동을 더 잘 노출함을 확인
- Binary human-calibration 생성/채점/변조탐지 테스트 구현 및 sealed source run 비변경 검증

위 수치는 개발 검증 증빙이며 공인 성능 성적을 주장하지 않는다.

## 15단계 작성 전 내부 검증 결과

15단계 이메일 최종 작성 전에 아래 조건을 모두 확인했다.

- 전체 unit/integration test: **85/85 PASS**
- dataset raw/scenario identity 재생성 검증: **PASS**
- official runtime evaluator source SHA 재동결 및 직접 validation: **PASS**
- evaluator repository clean commit: **PASS**
- `doctor --official --live --require-ready`: **READY / 필수 check PASS**
- clean commit 기준 AJQG 포함 live smoke: **PASS**
- live smoke SUT completion 1/1, evaluator/infrastructure failure 0, SUT source stable: **PASS**
- live smoke `procedure_valid=true`, `seal_verified=true`, explicit seal verify: **PASS**
- 문서의 protocol/Rubric/runtime 설명과 코드 정합성: **PASS**

따라서 15단계 이메일 초안은 위 검증 이후 최종 갱신했다. 최종 제품 성능 합격선과 공인 425-case 시험 수행 자체는 시험기관 협의 이후의 외부 단계다.
