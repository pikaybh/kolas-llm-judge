# 시험기관 협의용 Method Decision Register

- Evidence/Working ID: `METHOD-DECISION-REGISTER-20261011`
- 상태: `PROPOSAL / LAB APPROVAL REQUIRED`
- 기준일: `2026-10-11`
- 연결 문서: `01_TEST_METHOD.md`

> 목적: 시험기관이 각 항목을 **승인 / 수정 / 보류**하기 쉽게 현재 구현, SEEXR 권고안, 대안, 결과 영향을 한 곳에 모은다. 이 문서의 권고값은 시험기관 승인 전 공식 시험조건이 아니다.

## 1. 결정요약

| Decision ID | 항목 | SEEXR 권고안 | 승인 전 상태 |
|---|---|---|---|
| `DEC-METHOD-001` | Primary measurand | Hazard Semantic Identification Recall | 승인 필요 |
| `DEC-METHOD-002` | MATCH rule | `same_hazard_mechanism AND context_compatible` | 승인 필요 |
| `DEC-METHOD-003` | Denominator | **End-to-end: 선택된 전체 reference** | 중요 승인 필요 |
| `DEC-METHOD-004` | Dataset | `KOLAS_RA_GT v1.0.0`, 425 scenarios / 843 refs | 승인 필요 |
| `DEC-METHOD-005` | full run 반복횟수 | **2회** | 승인 필요 |
| `DEC-METHOD-006` | 반복 변동 판정 | 1차적으로 보고값 + 사전 합의된 tolerance; 아래 권고 참조 | 승인 필요 |
| `DEC-METHOD-007` | Judge 적격성 | frozen AJQG mandatory; human meta-validation은 추가요구 시 | 승인 필요 |
| `DEC-METHOD-008` | 제품 성능 합격선 | **시험기관/발주 규격이 요구하지 않으면 측정값 보고 방식 권고** | 승인 필요 |
| `DEC-METHOD-009` | Secondary 지표 | Completion Rate + repeatability를 최소 포함 | 승인 필요 |
| `DEC-METHOD-010` | GT와 RA retrieval DB 중복의 시험조건/해석 | 현재 통합제품 시험 시 overlap 공개; 독립 holdout 요구 시 별도 dataset/runtime freeze | **중요 승인 필요** |

## 2. DEC-METHOD-001 — Primary measurand

### 권고

**Hazard Semantic Identification Recall**을 primary measurand로 유지한다.

Reference hazard `r`이 식별된 것으로 보는 조건:

```text
∃ generated hazard g:
  same_hazard_mechanism(r,g) = true
  AND
  context_compatible(r,g) = true
```

### 이유

- 단순 문자열 일치보다 실제 위험 발생 메커니즘 식별능력을 측정한다.
- Recall은 GT 위험요인을 얼마나 누락 없이 찾아내는가라는 시험목적과 직접 연결된다.
- accident type만 우연히 같아도 MATCH로 계산되는 것을 방지한다.

### 승인 시 영향

현재 evaluator/rubric과 일치하므로 코드 변경 없음.

## 3. DEC-METHOD-002 — MATCH rule

### 권고

`same_hazard_mechanism AND context_compatible`를 유지한다.

### 승인하지 않을 경우

MATCH semantics가 변경되면 다음을 새 version으로 재동결해야 한다.

- rubric
- prompt
- AJQG control/gate 검토
- evaluator source identity
- 기존 성능결과 재평가 또는 재시험

## 4. DEC-METHOD-003 — Denominator

### 현재 구현 A

```text
references_with_completed_binary_match_matrix
```

SUT가 결과를 생성하지 못한 scenario의 reference는 Recall 분모에서 제외되고 Completion Rate에만 실패로 남는다.

### SEEXR 권고 B — End-to-end denominator

```text
all selected reference hazards
```

SUT non-completion scenario의 reference는 **identified=false**로 처리한다.

### B를 권고하는 이유

1. 공인 성능시험의 대상은 Judge만이 아니라 **SEEXR 시스템 전체 위험요인 식별능력**이다.
2. 결과 생성 실패가 많을수록 Recall 분모가 작아져 수치가 낙관적으로 보이는 현상을 방지한다.
3. Completion Rate와 Recall을 따로 보더라도 primary 지표 자체가 end-to-end 실패를 반영하므로 해석이 명확하다.
4. evaluator/infrastructure failure와 SUT failure는 이미 별도 taxonomy가 있으므로, 시험절차 오류를 제품 실패와 분리할 수 있다.

### 권고 failure rule

| Failure | Primary Recall | Procedure validity |
|---|---|---|
| `sut_non_completion` | 해당 scenario refs = missed | 유지 |
| `evaluator_failure` | 계산 중단 | candidate invalid |
| persistent `infrastructure_failure` | 계산 중단 | candidate invalid |

### 승인 시 필요한 작업

현재 구현 A와 달라지므로 시험 전에:

- metric version 증가
- aggregation code/test 수정
- 문서/official runtime hash 갱신
- AJQG가 아닌 deterministic metric regression 수행
- clean dry-run 수행

**기관 승인 전에는 코드 변경하지 않는다.**

## 5. DEC-METHOD-004 — Dataset 범위

### 권고

- `KOLAS_RA_GT v1.0.0`
- 425 scenarios
- 843 reference hazards
- canonical raw/scenario SHA-256 고정

GT content 변경 시 새로운 dataset version으로 올리고 기존 시험과 직접 혼합하지 않는다.

## 6. DEC-METHOD-005 — Full run 반복횟수

### 권고

동일 frozen 조건으로 **full 425-case run 2회**.

### 이유

- 최소한의 run-to-run stochastic variability를 직접 관찰할 수 있다.
- 비용·시간과 재현성 확인 사이의 균형이 현실적이다.
- 현 framework와 시험기관 제안서가 이미 2회 이상을 기본안으로 사용한다.

### 3회 이상이 필요한 경우

시험기관이 불확도 추정이나 분산 추정을 더 엄격히 요구하면 시험 시작 전에 `3회` 등으로 올린다. 시험 후 결과를 보고 반복횟수를 바꾸지 않는다.

## 7. DEC-METHOD-006 — 허용 변동 기준

### 현재 확보된 개발 증적

10-case repeat pilot:

- Run 1 strict recall: `17/21 = 80.95%`
- Run 2 strict recall: `16/21 = 76.19%`
- absolute difference: `4.76 percentage points`
- reference-level detection consistency: `20/21 = 95.24%`

이 표본은 작으므로 **이 수치를 그대로 공인 합격선으로 역설계하지 않는다.**

### 권고 보고항목

full repeat run에 대해 최소 다음을 보고한다.

- 각 run Recall
- mean
- sample standard deviation
- min / max / range
- absolute run-to-run difference (percentage points)
- reference-level detection consistency
- discordant reference 목록 및 scenario ID

### 시험기관에 제안할 tolerance 후보

기관이 반드시 Pass/Fail tolerance를 요구하는 경우에 한해 다음을 **협의 시작점**으로 제안할 수 있다.

```text
reference-level detection consistency >= 95%
AND
absolute primary Recall difference <= 5 percentage points
```

주의:

- 이는 아직 공식 threshold가 아니다.
- 10-case pilot이 95.24% / 4.76%p였다는 이유만으로 자동 승인하지 않는다.
- full 425-case 반복 결과를 본 후 threshold를 소급 변경해서는 안 된다.
- 기관이 측정 불확도/통계적 방법을 별도로 요구하면 그 방식을 우선한다.

### 더 보수적인 권고

시험기관이 tolerance 합격판정을 요구하지 않는다면 **반복결과를 정량 보고하되 Pass/Fail threshold는 두지 않는 방식**이 가장 과도한 사후 기준설정을 피할 수 있다.

## 8. DEC-METHOD-007 — Judge qualification

### 권고

공식 run 직전 frozen AJQG를 mandatory gate로 사용한다.

현재 current-source qualification evidence:

- 104 controls × 2 repeats
- all gate metrics `1.0000`
- 376/376 repeated Boolean decisions identical
- gate PASS

Human meta-validation은 시험기관이 추가 요구하는 경우 별도 sample/threshold를 사전 합의해 수행한다.

## 9. DEC-METHOD-008 — 제품 성능 합격선

### 권고

**발주/인증 목적상 특정 최소 성능 기준이 명시되어 있지 않다면, 임의의 Recall 숫자를 SEEXR 측에서 먼저 “합격선”으로 만들지 않는다.**

권고 방식:

```text
measurement/reporting test
```

즉 승인된 방법으로 성능값·불확도/반복성을 측정하여 성적서에 보고한다.

### Pass/Fail이 반드시 필요한 경우

다음 순서로 시험 전에 고정한다.

1. 시험기관/발주 요구사항 확인
2. threshold의 기술·규격 근거 명시
3. threshold 값과 적용 지표/반올림 규칙 고정
4. runtime에 `performance_thresholds_frozen=true`로 반영
5. 시험 후 threshold 변경 금지

내부 과거 성능수치를 보고 threshold를 맞추는 방식은 사용하지 않는다.

## 10. DEC-METHOD-009 — Secondary 지표

### 최소 권고

성적서 또는 annex에 최소 다음을 primary와 구분해 보고한다.

1. SUT Completion Rate
2. run-to-run primary Recall variability
3. reference-level detection consistency
4. procedure validity / retry / non-completion count

나머지 사고유형·감소대책·법규 등의 내부 QA 지표는 이번 Hazard Identification 공식 scope와 분리한다.


## 11. DEC-METHOD-010 — GT와 RA retrieval DB 중복의 시험조건/해석

### 2026-10-13 확인 결과

SUT가 runtime에 사용하는 RA 검색 DB 6,443건과 GT 843건을 exact normalized 비교한 결과:

- hazard exact: `718/843 (85.1720%)`
- process + subprocess + hazard exact: `591/843 (70.1068%)`
- process + subprocess + equipment + material + hazard exact: `583/843 (69.1578%)`
- 8 textual fields exact: `194/843 (23.0130%)`

따라서 현재 dataset을 모든 SUT runtime knowledge와 독립된 holdout으로 표현하지 않는다. 상세 증적은 `15_TEST_DATA_INDEPENDENCE_AUDIT.md`와 `data/submission/evidence/gt_ra_overlap_audit_20261013.json`을 참조한다.

### 선택안 A — 현재 통합제품 end-to-end

RA DB를 SUT 구성요소로 포함하여 snapshot/hash를 freeze하고 overlap을 시험조건에 명시한다. 결과는 현재 통합제품의 end-to-end Hazard Identification 성능으로 해석한다.

### 선택안 B — 독립성 통제 시험

시험기관이 independent holdout을 요구하면 별도 비중복 시험셋 또는 leakage-controlled retrieval condition을 사전 합의하고 새 identity로 freeze한다.

### SEEXR 권고

시험 목적이 현재 제품 성능 확인이라면 A가 제품 실동작을 가장 직접 반영한다. 단, 독립 일반화 성능을 요구하는 시험이라면 B가 필요하다. 어느 쪽이든 **시험 시작 전에 결정하고 시험 후 결과를 본 뒤 조건을 변경하지 않는다.**

## 12. 기관 회신용 최소 선택표

시험기관은 아래 칸만 채워도 method freeze 작업을 진행할 수 있다.

| Decision | SEEXR 제안 | 기관 선택/수정 |
|---|---|---|
| Primary | Hazard Semantic Identification Recall |  |
| MATCH | mechanism AND context |  |
| Denominator | all 843 selected references / SUT non-completion=missed |  |
| Dataset | 425 scenarios / 843 refs |  |
| Full repeat | 2회 |  |
| Repeat tolerance | report-only 권고; 필요 시 95% consistency + ≤5%p를 협의 시작점 |  |
| Judge gate | frozen AJQG mandatory |  |
| Product threshold | 별도 규격 없으면 measured value report |  |
| Secondary | completion + repeatability 최소 포함 |  |
| GT↔RA overlap | 통합제품 end-to-end + overlap 명시 / 독립 holdout 요구 시 별도 조건 |  |

## 13. 승인 후 실행해야 할 자동 변경

Decision Register가 승인되면 다음 순서로 반영한다.

1. 승인값을 `01_TEST_METHOD.md`에 반영
2. 필요한 경우 metric version/code 수정
3. official runtime/version hash 갱신
4. regression test
5. current-source AJQG 재확인
6. SUT freeze candidate → final freeze
7. clean-room full run
8. HWP/HWPX의 붙임 1 및 버전/무결성 문서 갱신

기관 회신 전까지 이 문서는 `PROPOSAL` 상태를 유지한다.
