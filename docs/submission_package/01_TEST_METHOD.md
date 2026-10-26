# SEEXR 위험요인 식별 성능 시험방법 명세

- 문서 ID: `KOLAS-DOC-001`
- 버전: `0.2-draft`
- 상태: `REVIEW`
- 작성자: `{{AUTHOR}}`
- 검토자: `{{REVIEWER}}`
- 승인자: `{{APPROVER}}`
- 기준일: `2026-10-11`
- Evidence IDs: `EV-GT-001`, `EV-GT-003`, `EV-EVAL-001`~`EV-EVAL-006`, `EV-API-001`, `EV-SUT-001`~`EV-SUT-004`
- 관련 Git commit/tag: `{{FINAL_MEASUREMENT_RELEASE_TAG}}`
- 관련 GT version: `KOLAS_RA_GT v1.0.0`
- 관련 evaluator version: `binary-checklist-v1`

> 본 문서는 현재 구현과 기존 시험기관 협의안을 일치시키기 위한 **freeze candidate**이다. 13절의 시험기관 협의 필요 항목이 확정되기 전에는 `APPROVED` 또는 `FROZEN`으로 승격하지 않는다.

## 1. 시험 목적

본 시험은 **SEEXR 위험성평가 AI가 공정·세부공정·설비·물질/자재로 구성된 건설 작업정보를 입력받아, 사전에 확정된 기준 위험요인(Ground Truth)을 의미적으로 식별하는 성능을 측정**하는 것을 목적으로 한다.

문자열의 동일성이나 단순 사고분류 일치를 정답으로 보지 않고, 위험 발생 메커니즘과 작업·노출 맥락의 의미적 동일성을 사전 정의된 Boolean Rubric으로 판정한다.

## 2. 시험대상과 시험 단위

### 2.1 시험대상 시스템(SUT)

- 서비스: SEEXR 위험성평가 AI
- SUT agent: `risk-assessment`
- 호출 방식: SEEXR Core API를 통한 live inference
- 현재 freeze candidate의 제품 실행 프로필: `modelMode=fast` → `quick-fast-v1.0.0`
- 위험성평가 방식: `빈도강도법 5x4`
- reasoning style: `balanced`

최종 공인시험 전에는 SUT Core/Agents를 clean commit/tag 상태로 별도 freeze하고, 해당 버전을 `12_VERSION_MANIFEST.md`에 기록한다.

### 2.2 Scenario

시험 scenario는 GT 원본에서 **`공정 + 세부공정` 조합**을 기준으로 구성한다. 하나의 scenario는 1개 이상의 reference hazard를 가질 수 있다.

현재 `KOLAS_RA_GT v1.0.0`은:

- 425 scenarios
- 843 reference hazards
- 843 source rows

으로 구성된다.

### 2.3 SUT 입력과 비공개 GT

SUT에 제공하는 입력은 다음 필드에 한정한다.

- 공정
- 세부공정
- 설비
- 물질/자재

다음 정보는 SUT에 제공하지 않고 평가용 reference로만 보존한다.

- 위험요인
- 사고분류
- 위험성 관련 값
- 감소대책
- 관련 법규

## 3. Generated Risk의 측정 단위

현재 측정 프로그램은 SUT 출력 `<risk_assessment>` XML의 `./items/item` **한 항목을 generated risk 한 개로 정의**한다.

- XML 첫 번째 item → `g001`
- 두 번째 item → `g002`
- 이후 동일 방식으로 순차 ID를 부여

측정 프로그램은 한 item의 `hazard` 또는 `hazard_analysis` 문장을 추가 LLM이나 의미분석으로 재분해하지 않는다. 즉 본 시험에서의 generated-risk unit은 **semantic atomicity를 추정한 단위가 아니라 SUT가 구조적으로 출력한 XML item 단위**다.

이 규칙은 동일 raw output을 항상 동일 generated-risk set으로 파싱하기 위한 deterministic contract다.

## 4. Reference × Generated 비교행렬

정상 파싱된 각 scenario에 대해 모든 reference hazard와 모든 generated risk의 Cartesian product를 평가한다.

예를 들어 reference 2개와 generated risk 3개가 있으면 6개의 pair를 Judge에 평가한다.

각 pair에는 최소 다음 정보가 제공된다.

- scenario context
- reference hazard
- generated hazard
- 필요한 사고분류/감소대책/법규 context

2026-10-26 방법 적합성 보강 자료: [`15_METHOD_VALIDITY_AND_API_KEY.md`](./15_METHOD_VALIDITY_AND_API_KEY.md) — 비교행렬 수식, 기존 넓은 KPI의 공학적 용도, 엄격 주지표와의 구분, A-only 허위양성 전문가 검증, 분모·KOLAS 승인과 API Key 절차를 설명한다. 본문의 공식 Primary는 시험기관의 변경 승인 전까지 유지한다.

## 5. 위험요인 식별 Boolean Rubric

각 `reference hazard × generated risk` pair에 대해 다음 Boolean을 판정한다.

| 판정항목 | True 기준 | Primary 사용 여부 |
|---|---|---|
| `same_hazard_mechanism` | 핵심 위험원→사건→피해 메커니즘이 실질적으로 동일 | 사용 |
| `context_compatible` | 작업·설비·노출 맥락이 동일하거나 함께 성립할 수 있을 정도로 양립 가능 | 사용 |
| `accident_compatible` | 사고유형 또는 피해 메커니즘이 동일·양립 가능 | Primary에는 미사용 |

KOLAS primary MATCH 규칙은 다음과 같이 고정한다.

`MATCH = same_hazard_mechanism AND context_compatible`

따라서 다음은 MATCH로 인정하지 않는다.

- 사고분류만 같은 경우
- 동일 키워드만 포함하는 경우
- 위험 메커니즘은 비슷하지만 해당 작업 맥락에서 양립할 수 없는 경우

반대로 표현이 다르더라도 핵심 위험 메커니즘과 맥락이 같으면 MATCH로 인정할 수 있다.

## 6. Reference-level 식별 규칙

### 6.1 여러 generated risk → 하나의 reference

하나의 reference hazard에 대해 generated risk 중 **하나 이상**이 MATCH이면 해당 reference는 `identified=true`다.

여러 generated risk가 같은 reference에 MATCH되어도 numerator에는 reference 1건으로만 계산한다.

### 6.2 하나의 generated risk → 여러 reference

하나의 generated risk가 여러 reference와 각각 독립적으로 MATCH 조건을 충족할 경우, 여러 reference를 식별할 수 있다.

따라서 KOLAS primary Recall에는 Hungarian 1:1 uniqueness를 강제하지 않는다. 이는 **reference-level many-to-one identification**이다.

### 6.3 Hungarian matching의 역할

Hungarian maximum-cardinality 1:1 matching은 `Reference Risk Coverage` 및 일부 matched quality 지표를 위한 **secondary/diagnostic** 절차이며, primary Recall numerator를 결정하지 않는다.

## 7. Primary 지표

공식 지표명은 다음을 freeze candidate로 사용한다.

**Hazard Semantic Identification Recall**
내부 metric key: `hazard_semantic_identification_recall`

### 7.1 Numerator

정상적으로 binary match matrix가 완료된 reference 중, 하나 이상의 generated risk와

`same_hazard_mechanism=true AND context_compatible=true`

인 reference 수다.

### 7.2 현재 구현의 Denominator

현재 코드·runtime·시험방법 문서가 일치하여 사용하는 denominator는:

`references_with_completed_binary_match_matrix`

즉 **binary match matrix가 정상적으로 완료된 reference hazard 수**다.

현재 구현에서는 SUT non-completion으로 case result가 생성되지 않으면 해당 scenario의 reference는 primary Recall denominator에서 제외되고, SUT completion rate에 별도로 반영된다.

### 7.3 Denominator 정책의 시험기관 승인 필요성

위 정책은 현재 구현에 대해 완전히 재현 가능하지만, 공인시험 관점에서는 다음 두 방식 중 무엇을 primary로 할지 시험기관과 명시적으로 합의해야 한다.

| 정책 | 분모 | SUT non-completion 처리 | 장점/주의점 |
|---|---|---|---|
| A. 현재 구현 | match matrix가 완료된 reference | Recall 분모에서 제외, completion rate에 별도 반영 | semantic Judge가 실제 평가한 표본만 측정. 단, non-completion이 많을수록 Recall이 낙관적으로 보일 수 있음 |
| B. End-to-end | 선택된 모든 reference | 식별 실패로 계산 | 시스템 전체 위험요인 식별 성공률을 직접 반영. evaluator failure와 SUT failure 구분 규칙을 더 엄격히 정의해야 함 |

**현재 freeze candidate는 A이며, 시험기관 승인 전 이를 최종 공인 denominator로 선언하지 않는다.** 필요 시 승인된 정책으로 metric version을 올리고 코드/runtime/test를 함께 변경한다.

## 8. SUT 실패 및 시험 인프라 실패 처리

현재 failure taxonomy는 다음과 같다.

### 8.1 `sut_non_completion`

다음은 제품 결과의 실패로 기록하되 시험절차 자체를 자동 무효화하지 않는다.

- 충분한 입력인데 `<ask_user>` 반환
- invalid `<risk_assessment>` XML
- `<risk_assessment>` 누락
- parsing 불가 SUT output
- SUT run terminal failure / final content 누락

현재 denominator 정책 A에서는 이 case의 reference가 primary Recall에서 제외되고, `SUT Completion Rate`에 실패로 기록된다.

### 8.2 `evaluator_failure`

예:

- Judge/evaluator가 retry 후에도 실패
- 결과 조립 실패

공식 candidate를 무효화한다.

### 8.3 `infrastructure_failure`

예:

- SUT transport/API failure가 bounded retry 이후에도 지속

공식 candidate를 무효화한다.

## 9. Retry 및 Timeout 규칙

### 9.1 SUT

현재 official runtime freeze candidate:

- timeout: 1200초
- `max_retries=3`
- 초기 backoff: 0.5초
- 지수 backoff: `0.5 × 2^retry_index`, 최대 5초
- run 생성: 최초 시도 + 최대 3회 retry
- SSE stream: last durable sequence 이후 재연결, 최대 3회 reconnect
- 같은 run 생성 retry에는 동일 `client_request_id`를 사용하여 중복 생성 위험을 줄인다.

retryable 조건에는 transport/timeout과 사전에 정의된 retryable HTTP status가 포함된다.

### 9.2 Judge

- request timeout: 180초
- OpenAI SDK `max_retries=3`
- bounded retry 후에도 Judge가 실패하면 `evaluator_failure`로 분류하여 official candidate를 무효화한다.

## 10. 절차 유효성

공식 candidate는 최소 다음을 모두 만족해야 한다.

1. official runtime validation 성공
2. AJQG 통과
3. 모든 selected case가 `result` 또는 명시적 error 결과로 처리
4. evaluator/infrastructure failure 0건
5. 시험 시작·종료 사이 SUT relevant source fingerprint 동일
6. 최종 run seal verification 성공

SUT non-completion은 현재 procedure validity를 자동으로 무효화하지 않고 별도 제품 outcome으로 기록한다.

## 11. 재현성 평가

동일한 다음 조건으로 live run을 반복한다.

- 동일 GT version/hash
- 동일 SUT release/config
- 동일 Judge model/config
- 동일 prompt/rubric
- 동일 parser/metric code
- 동일 API method 및 failure policy

현재 시험방법 제안은 **동일 조건 full run 최소 2회**를 기본으로 한다. 시험기관이 다른 반복 횟수를 요구하면 시험 시작 전에 해당 횟수를 freeze한다.

반복 run 간 다음을 계산한다.

- primary Recall의 mean
- sample standard deviation
- min / max / range
- case별 metric 차이
- reference별 `identified` Boolean의 일치 비율
- 모든 run에서 동일한 detection state를 가진 reference 비율

생성 텍스트의 byte/string 동일성은 재현성 지표로 사용하지 않는다.

## 12. Secondary / Diagnostic 지표

Primary와 구분하여 다음을 보고할 수 있다.

- SUT Completion Rate
- Reference Risk Coverage (Hungarian 1:1)
- Accident Classification Agreement
- Mitigation Appropriateness
- Mitigation Actionability
- Mitigation Specificity
- Legal Basis Presence / Relevance
- Unsafe Advice Rate
- Critical Safety Error Rate
- Schema Compliance
- frequency/severity 범위 및 `risk = frequency × severity` deterministic consistency
- supplementary `hazard_identification_accuracy`

supplementary `hazard_identification_accuracy`는

`(same_hazard_mechanism AND context_compatible) OR accident_compatible`

로 primary보다 넓으므로 공식 primary와 혼용하지 않는다.

## 13. 시험기관 협의·승인 필요 항목

| Decision ID | 항목 | 현재 freeze candidate | 최종 상태 |
|---|---|---|---|
| `DEC-METHOD-001` | Primary measurand | Hazard Semantic Identification Recall | 시험기관 승인 필요 |
| `DEC-METHOD-002` | MATCH rule | mechanism AND context | 시험기관 승인 필요 |
| `DEC-METHOD-003` | Denominator | completed binary match matrix references | **특히 승인 필요**; end-to-end 방식과 비교 설명 필요 |
| `DEC-METHOD-004` | Dataset 범위 | 425 scenarios / 843 refs | GT validation 이후 승인 필요 |
| `DEC-METHOD-005` | 반복횟수 | full run 최소 2회 | 시험기관 승인 필요 |
| `DEC-METHOD-006` | 허용 변동 기준 | 아직 미확정 | 시험기관과 결정 필요 |
| `DEC-METHOD-007` | Judge 적격성 | frozen AJQG + 별도 human meta-validation 가능 | 시험기관 승인 필요 |
| `DEC-METHOD-008` | 성능 합격선 | `report_only_until_testing_lab_approval` | 시험기관과 결정 필요 |
| `DEC-METHOD-009` | 성적서 secondary 지표 | 12절 후보 | 시험기관과 결정 필요 |

## 14. HWP 반영 지시

본 문서는 최종 HWP의 **붙임 1. 시험방법 및 시험대상 시스템 명세서**의 시험방법 부분에 반영한다.

필수 표:

- 표 1. 시험대상·입력·GT 요약
- 표 2. Boolean MATCH Rubric
- 표 3. Primary numerator/denominator 정의
- 표 4. Failure taxonomy와 공식 candidate 영향
- 표 5. 시험기관 협의 필요 항목

필수 그림:

`Scenario input → SUT → XML item parsing → Reference×Generated Boolean matrix → Reference-level Recall → Report/Seal`

## 15. 승인 차단조건

다음이 해결되지 않으면 이 문서를 `APPROVED/FROZEN`으로 변경하지 않는다.

- `DEC-METHOD-003` denominator 정책 미승인
- `DEC-METHOD-005/006` 반복 횟수·허용 변동 미승인
- `DEC-METHOD-008` 성능 합격선 미승인
- Phase 3/4의 GT provenance·전문가 검증 미완료
- 최종 SUT clean release 미지정

## 16. 변경이력

| 버전 | 일자 | 변경내용 | 상태 |
|---|---|---|---|
| 0.2-draft | 2026-10-11 | 실제 코드/runtime/parser/failure policy와 기존 시험기관 제안서를 통합하고 denominator 의사결정 gap 명시 | REVIEW |
