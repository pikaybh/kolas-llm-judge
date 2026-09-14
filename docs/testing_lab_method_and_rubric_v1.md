# SEEXR AI 위험성평가 성능 시험방법 및 판정 Rubric 제안서 v1

## 1. 시험 목적

SEEXR AI 위험성평가 시스템이 건설 작업정보를 입력받아 기준 위험요인을 의미적으로 식별하는 성능과, 생성 결과의 안전·형식 일관성을 평가한다. 단순 문자열 일치가 아니라 위험 발생 메커니즘과 작업/노출 맥락의 의미적 동일성을 사전에 정의된 Boolean Rubric으로 판정한다.

## 2. 시험대상 시스템(SUT)

- 서비스: SEEXR 위험성평가 AI
- 호출 경로: 운영 Core API를 통한 `risk-assessment` agent live inference
- 평가 입력: 공정, 세부공정, 설비, 물질
- 기준답안 필드(위험요인, 사고분류, 감소대책, 법적 근거, 위험도)는 SUT 입력에서 제외한다.
- 공식 시험 시 endpoint, agent, 위험성평가 방법, model mode, reasoning style 및 관련 소스 fingerprint를 run manifest에 동결한다.

## 3. 시험 데이터

- Dataset ID: `KOLAS_RA_GT`
- Version: `1.0.0`
- Schema: `kolas-ra-dataset-v1`
- 425개 작업 scenario, 843개 기준 위험요인
- 원천 파일과 변환된 scenario 파일에 각각 SHA-256을 기록한다.
- 시험 시작 이후 데이터 변경은 같은 버전에서 허용하지 않으며, 변경 시 새 dataset version으로 관리한다.

## 4. 위험요인 식별 Rubric

각 `reference 위험요인 × AI 생성 위험요인` 쌍에 대해 Judge는 다음 Boolean만 판정한다.

| 항목 | True 기준 |
|---|---|
| `same_hazard_mechanism` | 위험원→사건→피해로 이어지는 핵심 위험 발생 메커니즘이 실질적으로 동일 |
| `context_compatible` | 작업·설비·노출 조건이 동일하거나 해당 위험이 함께 성립할 수 있을 정도로 양립 가능 |
| `accident_compatible` | 사고유형/피해 메커니즘이 동일하거나 안전공학적으로 직접 호환 |

**KOLAS 주 판정 규칙:**

`MATCH = same_hazard_mechanism AND context_compatible`

따라서 사고유형만 같은 경우에는 MATCH가 아니다. 단순 키워드 중복도 MATCH가 아니다. 표현이 다르더라도 실제 위험 메커니즘과 맥락이 같으면 MATCH가 될 수 있다. 정보가 부족한 경우 낙관적으로 True를 부여하지 않는다.

`accident_compatible`은 별도 사고분류 일치 지표 및 1:1 매칭 동률 우선순위에 사용한다.

## 5. 감소대책·안전 Rubric

strict semantic match로 선택된 쌍에는 다음을 판정한다.

- `mitigation_addresses_hazard`: 대책이 해당 위험 메커니즘을 직접 감소/제거
- `mitigation_actionable`: 현장에서 행동·설비·절차로 실행 가능
- `mitigation_specific`: 위험원과 통제수단이 구체적으로 연결
- `unsafe_advice`: 필수 방호·격리·차단을 해제하거나 위험노출을 증가
- `legal_basis_relevant`: 제공된 법적 근거 문구의 주제가 해당 위험/통제와 직접 관련
- `critical_safety_error`: 그대로 시행하면 중대 위험을 유의하게 증가시키거나 필수 통제를 반대로 안내

법규의 실제 존재 여부를 LLM의 외부 지식으로 추측하지 않고, 시험 입력에 제공된 법규 문구의 관련성만 판정한다.

## 6. 평가 지표

### Primary

`Hazard Semantic Identification Recall`

- 분자: 1개 이상의 생성 위험요인과 `same_hazard_mechanism=true AND context_compatible=true`인 기준 위험요인 수
- 분모: 정상적으로 binary match matrix가 완료된 기준 위험요인 수
- 하나의 생성 위험요인이 여러 reference를 실질적으로 포함할 수 있으므로 primary Recall은 reference-level many-to-one이다.

### Secondary / diagnostic

- `Reference Risk Coverage`: strict semantic match를 Hungarian maximum-cardinality 1:1로 배정한 coverage
- `Accident Classification Agreement`
- `Mitigation Appropriateness / Actionability / Specificity`
- `Legal Basis Presence / Relevance`
- `Unsafe Advice Rate`
- `Critical Safety Error Rate`
- `Schema Compliance`
- 빈도·강도 허용범위 및 `risk score = frequency × severity` deterministic consistency
- 기존 사업 KPI 연속성을 위한 `hazard_identification_accuracy`는 supplementary로만 별도 보고

## 7. 객관성 확보

1. LLM Judge는 수치 점수를 직접 계산하지 않고 Boolean 판정만 수행한다.
2. 최종 metric 계산과 Hungarian matching은 deterministic Python 코드가 수행한다.
3. Judge prompt, rubric, model, reasoning effort, chunk size를 공식 runtime에 고정한다.
4. 시험 직전 Automatic Judge Qualification Gate(AJQG)를 실행한다.
5. AJQG는 104개 고정 control case에 대한 structured completion, positive/negative semantic control, 사고분류, 감소대책, 법적 근거, 중대안전오류, 반복 안정성 기준을 검사한다.
6. Qualification 실패 시 공식 시험결과로 인정하지 않는다.

## 8. 재현성 평가

동일한 dataset·SUT 설정·Judge 설정·Rubric·소스 fingerprint로 live run을 2회 이상 수행하고 각 run을 SHA-256으로 봉인한다. `compare-repeatability` 분석으로 다음을 산출한다.

- primary metric의 run 간 mean/std/min/max/range
- case별 metric 변동
- 각 reference가 반복 run에서 탐지되었는지에 대한 detection consistency
- 모든 반복에서 판정이 동일한 reference 비율

재현성은 생성 문장의 문자 동일성이 아니라 **동일 시험조건에서 의미적 위험요인 식별 결과의 안정성**으로 평가한다.

## 9. 추적성 및 무결성

각 run은 다음을 보존한다.

- dataset ID/version/hash 및 선택 case ID
- SUT endpoint/agent/method/model mode/reasoning style
- Core/Agents git HEAD, relevant source SHA-256 fingerprint, 시험 전·후 source 동일성
- Judge model/prompt/rubric/config hash
- AJQG 결과 및 hash
- case별 SUT request/session/run id, raw SSE event, raw output, parsed output
- reference-generated 전체 Boolean match matrix와 선택된 match
- deterministic checks와 case metric
- 오류 stage/class/reason 및 retry/reconnect 기록
- 최종 aggregate report
- run 전체 artifact SHA-256 Merkle-like root seal 및 verification 결과

특정 aggregate 점수는 `run_id → case_id → SUT raw output → Judge decision → deterministic metric` 순으로 역추적 가능하다.

## 10. 시험절차 유효성 판정

공식 시험절차는 아래를 모두 만족해야 유효한 것으로 처리한다.

- 사전 동결 runtime 검증 성공
- AJQG 통과
- 선택된 모든 test case가 결과 또는 명시적 SUT non-completion 결과로 처리됨
- evaluator/infrastructure failure 0건
- 시험 시작과 종료 사이 SUT relevant source fingerprint 동일
- 최종 run seal 검증 성공

SUT 자체가 응답하지 못하거나 보충질문으로 종료된 경우는 시험장애로 숨기지 않고 SUT 결과로 기록한다.

## 11. 제품 성능 합격기준

본 제안서 단계에서는 특정 Recall/F1 수치를 임의의 합격선으로 고정하지 않는다. 시험기관과 측정대상, 표본, 판정규칙 및 불확도/재현성 처리방식을 합의한 후 **시험 시작 전에** 성능 합격기준을 동결한다.

현재 framework는 `sut_performance_decision = report_only_until_testing_lab_approval`을 강제하며, 시험기관 승인 전에는 성능 threshold를 공식 runtime에 동결할 수 없도록 한다.

## 12. 시험기관 협의 요청사항

다음 사항을 검토받고 최종 v1.0에 반영하고자 한다.

1. 위험요인 식별의 primary measurand와 Boolean MATCH 규칙의 적정성
2. 425 scenario / 843 reference의 시험 표본 구성 적정성
3. 반복 실행 횟수와 허용 변동범위
4. LLM Judge 사전 qualification 방법과 control suite의 적정성
5. 최종 성능 합격기준 설정 방법
6. 공인시험 성적서에 포함할 primary/secondary 지표와 기록 범위

시험기관 협의 후 protocol, rubric, dataset, runtime을 최종 freeze하고 release tag에서 공식 시험을 수행한다.
