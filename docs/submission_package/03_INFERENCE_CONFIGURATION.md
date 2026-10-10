# SEEXR 위험성평가 AI 추론 설정 및 모델 구성 명세

- 문서 ID: `KOLAS-DOC-003`
- 버전: `0.2-draft`
- 상태: `REVIEW`
- 기준일: `2026-10-11`
- Freeze candidate: `SEEXR-RA-SUT-RC-2026.10.11.1`
- Agents source snapshot: `66eeb579b3e76b474e88a658b1e1acf53af6af25`

## 1. 목적

본 문서는 KOLAS 위험요인 식별 시험에서 SEEXR SUT 내부의 LLM 모델, prompt source, structured-output schema, tool, retrieval, provider-controlled parameter를 구분하여 기록한다.

중요 원칙은 **확인되지 않은 temperature/seed 등의 값을 추정해 적지 않는 것**이다.

## 2. 제품 실행모드와 Provider 처리모드의 구분

SEEXR의 `modelMode=fast`는 제품 내부 execution profile 선택값이다.

`risk-assessment + modelMode=fast` → `quick-fast-v1.0.0`

이는 OpenAI의 Fast mode / `service_tier=fast`와 동일한 개념이 아니다. 현재 quick-fast source에는 OpenAI `service_tier`를 직접 지정하는 코드가 확인되지 않았다.

따라서 제출 문서에서는 다음처럼 구분한다.

- **SEEXR execution profile:** `quick-fast-v1.0.0`
- **SEEXR UI/product mode:** `fast`
- **OpenAI serving/service tier:** 명시적으로 설정하지 않음 / framework-provider behavior

## 3. KOLAS 표준 입력에서의 실제 LLM 경로

시험계정 saved instruction을 empty로 고정하고, 사진·deviceContext·projectId·사고사례 explicit include가 없는 표준 KOLAS 입력을 전제로 한다.

### 3.1 항상 또는 정상경로에서 호출되는 모델

| Agent | 역할 | 모델 source identifier | 호출 설정 |
|---|---|---|---|
| `riskWorkClassifierAgent` | 작업 맥락 분류 | `openai/gpt-4.1` | `maxSteps=1`, Structured Output, 최대 2회 application-level validation attempt |
| `riskCandidateScopeValidatorAgent` | 검색 후보의 scope 적합성 검증 | `openai/gpt-4.1` | `maxSteps=1`, Structured Output, 최대 2회 validation attempt |
| `quickFastRiskDraftV1_0_0Agent` | 위험성평가 draft 생성 | `openai/gpt-4.1` | `maxSteps=1`, Structured Output, 최대 2회 validation attempt |
| `quickFastRiskVerifyV1_0_0Agent` | draft 검증/보정 | `openai/gpt-4.1` | `maxSteps=1`, Structured Output |

### 3.2 조건부 모델

| Agent | 모델 | KOLAS 표준조건에서의 상태 |
|---|---|---|
| `riskPolicyDecisionAgent` | `openai/gpt-4.1-mini` | user/project saved instruction이 empty이면 호출되지 않고 local fallback 사용 |
| `contextualRiskCandidateAgent` | `openai/gpt-4.1` | `deviceContext`가 없어 environment context가 없으므로 표준 KOLAS에서는 skip 대상 |
| `photoAgent` | `openai/gpt-4o` | image/attachment가 없어 표준 KOLAS에서는 실질적 호출 없음 |
| `accidentAgent` | `openai/gpt-4o` | accident-cases가 omit이면 skip |

따라서 **정상 KOLAS test path의 생성 LLM은 사실상 GPT-4.1 계열 4단계**로 구성되는 것이 목표다. saved instruction, 사진, 환경 context, 사고사례 flag가 달라지면 호출 graph가 달라질 수 있으므로 이 입력상태도 함께 freeze해야 한다.

## 4. 모델 alias와 snapshot

현재 source는 `openai/gpt-4.1`, `openai/gpt-4o`, `openai/gpt-4.1-mini`처럼 alias형 identifier를 사용한다.

OpenAI 공식 모델 문서는 GPT-4.1에 고정 snapshot `gpt-4.1-2025-04-14`를 제공하고, snapshot은 모델의 특정 버전을 고정하여 behavior consistency를 높이는 용도라고 설명한다.

- GPT-4.1: `https://developers.openai.com/api/docs/models/gpt-4.1`
- GPT-4o: `https://developers.openai.com/api/docs/models/gpt-4o`

GPT-4o에는 여러 snapshot이 제공된다.

현재 제품 source를 임의로 snapshot identifier로 변경하지 않는다. 변경 시 SUT 자체가 달라지기 때문이다.

공인시험 전 다음 중 하나를 `DEC-INF-001`로 승인한다.

**A. 현재 alias 유지**

- 실제 provider response의 resolved model identifier를 각 LLM call evidence에 기록
- 시험기간 alias behavior가 바뀌지 않았음을 provider evidence로 확인 가능한 범위에서 기록
- 재현성 수준은 snapshot pinning보다 약함

**B. snapshot pinning**

- SUT release에서 승인된 snapshot identifier를 직접 지정
- 변경 전/후 validation 후 해당 build를 시험대상 제품 버전으로 선언
- production/test 동일성 정책을 별도 명시

재현성을 최우선으로 하면 B가 강하지만, 이는 제품 설정 변경이므로 시험대상 정의 승인 없이 자동 적용하지 않는다.

## 5. Sampling / token / reasoning 관련 파라미터

현재 quick-fast 관련 `.generate()` 호출과 agent definition을 코드 기준으로 감사한 결과:

| Parameter | SUT source 상태 | 문서화 방식 |
|---|---|---|
| `temperature` | 명시 없음 | `UNSET / framework-provider controlled` |
| `top_p` / `topP` | 명시 없음 | `UNSET / framework-provider controlled` |
| `seed` | 명시 없음 | `UNSET / provider controlled` |
| `max_output_tokens` | 명시 없음 | `UNSET / model/framework default` |
| `maxTokens` | relevant quick-fast 호출에 명시 없음 | `UNSET` |
| reasoning effort | GPT-4.1 SUT 호출에 별도 명시 없음 | `UNSET / not a reasoning-model control in current source` |
| OpenAI `service_tier` | 명시 없음 | `UNSET` |
| `maxSteps` | 대부분 `1`; accidentAgent `5` | agent/tool-loop step cap이며 token cap이 아님 |
| structured output | classifier/scope/draft/verify/policy에 사용 | Zod schema source와 함께 freeze |

숫자가 코드 또는 provider response에서 확인되지 않는 값은 최종 문서에도 임의 숫자로 쓰지 않는다.

## 6. Prompt / instruction source freeze

SEEXR prompt는 단일 `.md` 파일이 아니라 agent source와 runtime context를 조합해 만들어진다. 따라서 prompt identity는 관련 source hash 집합으로 관리한다.

### 6.1 핵심 agent source hash

| Source | SHA-256 |
|---|---|
| `riskWorkClassifierAgent.ts` | `b462f6bb1c0065988d1f0e269c2d31fb49693fd22ec493fbf1cddd05d446bfe2` |
| `riskCandidateScopeValidatorAgent.ts` | `3841129cf4ee7bd7ce0d9c4c14f8e17dda92dcf34df164254cd295f0e88a6d53` |
| `quickFastRiskDraftV1_0_0Agent.ts` | `c47afd43bec4dbd262bb7a2f07fd5bea0cda6b9c80f2b2fde1be84f04ef10fef` |
| `quickFastRiskVerifyV1_0_0Agent.ts` | `3b3e715dcdbd85f8ae36fa14e6fa7f8a6d067de9af2477403d059a930ffa93e5` |
| `riskPolicyDecisionAgent.ts` | `79fb37d252cfee7c0d5de27e57a6b3f768e13e4e23a87351304e1f77811ae911` |
| `contextualRiskCandidateAgent.ts` | `9c3d5d101cf51bdc2a60676a99841952035ee23994e684202050dac2867f5ca5` |
| `photoAgent.ts` | `2539250e60afe3eb0ba050e5f317f5817761f46f1297babe2c35b58e68baa112` |
| `accidentAgent.ts` | `20b0b31d7ca9b369902c24bdce666860eb2087588b77dae79e225dbd0c73fe5f` |

### 6.2 Workflow / prompt-builder hash

| Source | SHA-256 |
|---|---|
| `quickFastRiskAssessmentWorkflow.ts` | `530a03c2858da98a1c033b378ab349364e477ae7104ac224873e47b8b6b9b464` |
| `quickFastRiskWorkflow.ts` | `bf3ed317dc37bd1e0705f67d1557f119c07696f70025ea67c39bcc1f98c3c8c1` |
| `riskWorkClassification.ts` | `5774aeb4d192c94787f15b24daaff9eca4651d6c17f48e8995628d5456be7f0d` |
| `riskCandidateScopeValidation.ts` | `7c765c8049160c296893d989a2f4a438c41cfcdc78dbe8ceb19faf752efef1b1` |
| `reasoningEnvironmentContext.ts` | `8b1fc968db6c039ebb66e32775bc1ee2048bbd97f030c3f208d60ac9394848c9` |
| `riskPersonalizationContext.ts` | `c75ff9971631f020d6109b6f32d2ad59b76d5ef4c3a90ca2ffe2c33a96f6db01` |
| `riskPolicyDecision.ts` | `5e1829c6ba6d406283a6c7c482ac1694aaf55499a1dda6398dad4af69bd10e8d` |
| `riskAssessmentMethod.ts` | `be05ac1f1cad1f5ff545a0908b77341e318b7992a52cbd73a33907265231ac01` |

최종 release에서는 개별 hash뿐 아니라 Agents Git tree와 relevant-source aggregate fingerprint를 함께 기록한다.

## 7. Structured Output / schema

quick-fast는 주요 LLM 단계에서 Zod structured output schema를 사용한다. schema는 workflow 및 관련 utility source 안에 정의되어 있으므로 다음을 freeze한다.

- classifier output schema
- candidate scope output schema
- draft output schema
- verify output schema
- policy decision output schema
- final `<risk_assessment>` deterministic formatter/parser contract

Structured Output은 결과 형식을 제한하지만 모델의 semantic decision randomness를 제거하는 기능은 아니다.

## 8. Retrieval configuration

위험 후보 검색은 별도 RA API의 hybrid retrieval 결과에 의존한다.

현재 effective/default candidate:

- retrieval embedding: `text-embedding-3-large`
- dimensions: `1536`
- RRF: semantic `0.45`, lexical `0.35`, structured `0.20`
- top candidate request: `40`
- visible candidate rows: `6,443`
- visible content SHA-256: `8d25e2b57701bc97aa61331f55f170655ec52950c555563ebfc8dba3f6f1a493`

이 embedding model은 **SUT 생성 모델과 별개의 retrieval model**이다.

최종 freeze 전 embedding vector 포함 DB snapshot identity를 반드시 추가한다.

## 9. Reasoning style

KOLAS official runtime:

`reasoningStyle = balanced`

현재 reasoning-style utility에서 contextual candidate 한도는 다음과 같이 정의된다.

- precision: 0
- balanced: 2
- exploratory: 6

그러나 표준 KOLAS 입력은 `deviceContext`를 주지 않으므로 environment context 자체가 없고, contextual candidate LLM 단계는 정상적으로 skip되는 것이 목표다.

따라서 최종 smoke에서는 단순히 payload가 balanced인지뿐 아니라 **실제 environment context가 absent이고 contextual generation이 수행되지 않았는지**도 event/trace 기준으로 확인한다.

## 10. 사고사례 옵션

quick-fast input schema의 기본 `includeAccidentCases`는 `false`다.

시험계정 saved instruction이 empty일 때 policy resolver는 LLM을 호출하지 않고 fallback `omit`을 사용한다. KOLAS 고정 메시지에도 사고사례 포함 요청이 없다.

목표 상태:

- `includeAccidentCases=false`
- `accidentCasesStatus=not_requested`
- `accidentAgent` 호출 없음

## 11. 이미지 옵션

KOLAS는 attachment/image를 입력하지 않는다.

목표 상태:

- image count = 0
- photo analysis 결과 없음
- `photoAgent` 호출 없음

## 12. 법규 verification

법규 verification은 별도 LLM agent가 아니라 `riskLegalBasis.ts`를 통해 Core `/api/law/search` 등 법규 API를 조회하는 경로를 포함한다.

따라서 법규 output의 재현성은 다음에 의존한다.

- Agents source
- Core law proxy source
- Law API source
- Law DB content state

Primary hazard semantic identification과 법규 secondary 지표를 문서에서 구분하되, 동일 XML을 재현해야 한다면 법규 state도 SUT freeze 범위다.

## 13. Provider/model response evidence 개선 필요

현재 KOLAS harness는 SUT 내부 각 LLM call의 provider response ID, resolved model, service tier, usage를 직접 수집하지 않는다. Core/Agents trace가 이를 제공하더라도 현재 시험 evidence bundle과 연결되어 있지 않다.

공인 release 전 다음 중 가능한 항목을 run ID와 연결해 보존한다.

- provider request/response correlation ID
- requested model identifier
- resolved response model identifier
- provider service tier/effective tier (노출되는 경우)
- token usage
- tool/structured-output failure/retry count
- model-call stage name

secret이나 전체 hidden reasoning은 보존하지 않는다.

## 14. Freeze Decisions / Gaps

| ID | 중요도 | 항목 | 상태 |
|---|---|---|---|
| `DEC-INF-001` | Critical | GPT-4.1 alias 유지 vs snapshot pinning | 승인 필요 |
| `GAP-INF-001` | High | SUT sampling/service tier가 명시적으로 고정되지 않음 | provider/framework 지원범위 확인 후 정책 확정 |
| `GAP-INF-002` | High | 내부 LLM call의 resolved model metadata가 KOLAS evidence에 연결되지 않음 | observability export 필요 |
| `GAP-INF-003` | Critical | saved user instruction에 따라 policy agent 및 execution decision이 달라질 수 있음 | evaluation account empty freeze |
| `GAP-INF-004` | Critical | RA embedding vector snapshot identity 없음 | DB snapshot/hash 필요 |
| `GAP-INF-005` | High | Law DB content identity 없음 | DB snapshot/hash 필요 |

## 15. HWP 반영 지시

최종 HWP에는 최소 다음 표를 넣는다.

- KOLAS standard path에서 호출되는 LLM agent/model 표
- conditional agent 및 skip 조건 표
- 명시/미명시 inference parameter 표
- prompt/source hash 표
- retrieval 설정 표
- provider-controlled parameter 및 재현성 제한사항 표
