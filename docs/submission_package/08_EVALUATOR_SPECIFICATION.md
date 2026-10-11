# Evaluator / LLM Judge 측정시스템 명세

- 문서 ID: `KOLAS-DOC-008`
- 버전: `0.1-review`
- 상태: `REVIEW`
- 기준일: `2026-10-11`
- Evaluator pipeline: `binary-checklist-v1`
- Official runtime: `official-runtime-v1`
- Primary metric rule: `hazard-semantic-identification-v1`
- Evidence IDs: `EV-EVAL-001`~`EV-EVAL-010`

> 본 측정시스템에서 LLM Judge는 최종 점수나 Recall을 직접 산출하지 않는다. Judge는 사전에 정의된 Boolean 판정만 반환하고, pair completeness 검증·match rule·reference-level aggregation·최종 metric 계산은 frozen Python 코드가 결정적으로 수행한다.

## 1. 역할과 측정 경계

SEEXR SUT가 생성한 위험요인과 `KOLAS_RA_GT v1.0.0` reference를 비교할 때 evaluator는 다음 세 층으로 분리된다.

1. **LLM Boolean Judge**: 의미적 관계 및 안전품질을 Boolean으로 판정
2. **Deterministic evaluator**: Boolean 결과의 누락/중복 확인, matching 및 metric 계산
3. **Official runtime validator**: model/prompt/rubric/control suite/dataset/evaluator source hash를 시험 전에 확인

KOLAS primary 성능지표는 `hazard_semantic_identification_recall`이며, reference-generated pair가 다음 두 Boolean을 모두 만족할 때만 semantic identification으로 인정한다.

```text
same_hazard_mechanism == true
AND
context_compatible == true
```

`accident_compatible` 단독 true는 primary identification으로 인정하지 않는다.

## 2. Judge model 및 API 설정

Official runtime의 frozen 설정은 다음과 같다.

| 항목 | 고정값 |
|---|---|
| pipeline | `binary-checklist-v1` |
| model identifier | `gpt-5.6-sol` |
| reasoning effort | `medium` |
| max concurrency | `12` |
| request timeout | `180 s` |
| max retries | `3` |
| store | `false` |
| API | OpenAI Responses API structured parse |

현재 `binary_judge.py` 호출은 `temperature`, `top_p`, `seed`, `max_output_tokens`, `service_tier`를 명시하지 않는다. 따라서 이 값들을 임의의 숫자로 제출문서에 기재하지 않는다.

실제 response metadata에는 `response_id`, `response_model`, token usage, elapsed time, row count가 보존된다. 과거 qualification evidence에서 응답 model은 `gpt-5.6-sol`로 기록되어 있다.

## 3. Frozen prompt 및 rubric

| Artifact | Version/Role | SHA-256 |
|---|---|---|
| `prompts/judge_binary_v1.md` | Judge instruction | `97884ac7d7440b8e3843b0eee357478275871f949d4ef305b5c52a1eb3bad0bf` |
| `configs/rubric_binary_v1.yaml` | Boolean rubric | `d6993b9c49a88e4d5389c8d72dde27d750d0880c57d2fd18d38e08ae3ae93a22` |
| `configs/official_runtime_v1.yaml` | official freeze envelope | `bc49cde29d7da64185c6d2f4ea8311e8e4df3e82622ec47c4f80e60d0135ec1e` |

Official runtime validator는 위 파일의 현재 hash가 frozen runtime에 기록된 값과 다르면 실행을 거부한다.

## 4. Structured output schema

### 4.1 Match

`MatchChecklistDecision`

- `id: str`
- `same_hazard_mechanism: bool`
- `context_compatible: bool`
- `accident_compatible: bool`

### 4.2 Quality

`QualityChecklistDecision`

- `id: str`
- `mitigation_addresses_hazard: bool`
- `mitigation_actionable: bool`
- `mitigation_specific: bool`
- `unsafe_advice: bool`
- `legal_basis_relevant: bool`

### 4.3 Safety

`SafetyChecklistDecision`

- `id: str`
- `critical_safety_error: bool`

각 stage는 expected ID set과 response ID set을 비교한다. duplicate ID, missing ID, extra ID가 있으면 evaluator completeness failure로 처리한다.

## 5. Pair evaluation flow

### 5.1 Match matrix

각 scenario에 대해 모든 reference × generated risk Cartesian pair를 구성한다.

```text
pair_id = reference_id + "::" + generated_id
```

각 pair에 대해 Match Boolean 3개를 요청하고, 모든 pair의 decision completeness를 확인한다.

Primary reference-level identification은 1:1 Hungarian assignment와 별개다. 한 reference에 대해 하나 이상의 generated risk가 primary semantic rule을 만족하면 해당 reference는 identified로 계산된다.

### 5.2 1:1 diagnostic matching

`_maximum_binary_matches()`는 Hungarian assignment를 사용하여 1:1 diagnostic match set을 생성한다.

우선순위는 다음과 같다.

1. `same_hazard_mechanism AND context_compatible`인 eligible pair만 사용
2. 최대 reference coverage
3. 동률이면 `accident_compatible` 우선
4. 마지막으로 deterministic stable tie-break

이 1:1 결과는 quality diagnostic 및 `reference_risk_coverage`에 사용되며, KOLAS primary semantic recall 자체는 many-to-one reference identification matrix에서 계산한다.

## 6. Deterministic metric calculation

Primary metric:

```text
identified_reference = any(
    pair.same_hazard_mechanism AND pair.context_compatible
    for pair in all generated risks for the reference
)

Hazard Semantic Identification Recall
= identified references / evaluated references
```

Supplementary KPI는 다음 broader rule을 사용한다.

```text
(same_hazard_mechanism AND context_compatible)
OR accident_compatible
```

Quality/safety diagnostics도 Boolean count로 계산되며 LLM이 소수점 점수를 직접 생성하지 않는다.

## 7. Frozen evaluator source

Official runtime은 evaluator source aggregate SHA-256을 다음 값으로 고정한다.

`78152ba3c9df69b4dfc837b15380b9e25a2f132ab9d9abc75ba11337b582fbc1`

현재 핵심 source 개별 hash:

| Source | SHA-256 |
|---|---|
| `src/kolas_llm_judge/binary_judge.py` | `6523cd65eeee33e618cefecbb68a6cb1ec394e85ca40898b88d49e53b7470cef` |
| `src/kolas_llm_judge/qualification.py` | `6d6cfe505f03cafada91fe5e571a6bdc1109a92d88003041a444d1c4d6c7ba20` |
| `src/kolas_llm_judge/qualification_controls.py` | `be759e962a2625bc4515768096895bd8078557a3a752b12c6be1c8326d3fa5d5` |
| `src/kolas_llm_judge/binary_evaluation.py` | `92ecedad4d246f9e91c0b5e3baf68628f4de728a0df96df2e105da9bd1dc3adb` |
| `src/kolas_llm_judge/identification.py` | `4f62b70e26cb37fa983f487d75a7ac9cffad1026dd202b7618574b1a136be71b` |

## 8. Automatic Judge Qualification Gate 연결

공식 시험 전에 AJQG를 실행한다. AJQG는 본 Judge가 frozen Boolean control suite를 gate 기준 이상으로 판정하는지와 반복 결정 안정성을 확인한다.

AJQG PASS가 아니면 official run을 시작하지 않는다.

AJQG의 expected Boolean은 **construction-defined control**이다. 즉 “두 번째 독립 전문가 정답 데이터셋”이라고 표현하지 않는다. Human–LLM meta-validation 경로는 별도로 구현되어 있지만 현재 official mandatory gate가 아니다.

## 9. Requalification trigger

다음 항목 중 하나라도 변경되면 기존 Judge qualification을 그대로 재사용하지 않고 AJQG를 다시 실행한다.

- Judge model identifier
- reasoning effort
- Judge prompt
- Boolean rubric
- structured output schema
- control seed
- control-generation code 또는 control suite hash
- AJQG gate threshold
- Boolean aggregation / primary match rule
- evaluator source aggregate hash
- OpenAI SDK/runtime 의존성의 의미있는 변경

시험 당일에도 동일 frozen 설정으로 AJQG를 새로 실행하여 PASS해야 한다.

## 10. 현재 상태와 제한

- frozen evaluator code/config: 확인 완료
- structured schema: 확인 완료
- deterministic aggregation: 확인 완료
- historical AJQG qualification evidence: 확보
- 2026-10-11 live 재qualification 시도: API authentication 401로 **Judge 판정 전에 중단**

마지막 항목은 Judge gate FAIL이 아니다. 시험용 credential을 갱신한 뒤 시험 직전 AJQG를 재실행해야 한다.
