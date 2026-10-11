# SEEXR 위험성평가 AI 시험대상 시스템(SUT) 명세

- 문서 ID: `KOLAS-DOC-002`
- 버전: `0.2-draft`
- 상태: `REVIEW`
- 기준일: `2026-10-11`
- Freeze candidate ID: `SEEXR-RA-SUT-RC-2026.10.11.1`
- 관련 시험방법: `01_TEST_METHOD.md`
- 관련 추론설정: `03_INFERENCE_CONFIGURATION.md`
- 관련 버전표: `12_VERSION_MANIFEST.md`

> 이 문서는 2026-10-11 현재 Green 개발환경을 읽기 전용으로 감사하여 만든 **시험대상 후보 명세**다. 현재 Green 개발환경 자체를 공인시험용 frozen deployment로 선언하지 않는다.

## 1. 시험대상 정의

시험대상은 사용자가 건설 작업정보를 입력했을 때 SEEXR Core API가 `risk-assessment` 요청을 수신하고, `quick-fast-v1.0.0` workflow를 통해 위험요인을 생성한 뒤 `<risk_assessment>` XML을 반환하는 end-to-end 기능이다.

시험대상 경계에는 단순 LLM 호출뿐 아니라 결과에 실질적으로 영향을 주는 다음 구성요소를 포함한다.

1. SEEXR Core API
2. SEEXR Agents / Mastra `quick-fast-v1.0.0`
3. 위험성평가 후보 검색 API 및 검색 DB (`agent-api-ra`)
4. 법규 검색 API 및 법규 DB (`seexr-api-law`) — 법규/secondary output에 영향
5. 시험 전용 사용자 계정의 저장 instruction 상태
6. 모델 provider 및 모델 identifier
7. runtime/package-lock 및 비밀이 아닌 실행환경 설정

## 2. 현재 Freeze Candidate 소스 식별값

| Component | Repository | Git HEAD | Git tree | 2026-10-11 상태 |
|---|---|---|---|---|
| Core | `/srv/green-server/seexr-api-core` | `279bc052830bca596183ecbe8378dd69d6722f15` | `91de2c76fa7cb96dc301ebf2e85abc8a560051d9` | KOLAS relevant source clean; repo 전체에는 untracked `apple-root-certs/` 1건 |
| Agents | `/srv/green-server/seexr-api-agents` | `86b7f1bfdefad8bac5eeee68e685277cd955f37c` | `62f1f1430a258adfed036bc4a815ca94f00e2f87` | clean; KOLAS model snapshot override path 포함 |
| RA search API | `/srv/green-server/agent-api-ra` | `b400f87ffc483764e8a8857e12c188867425c2b2` | `db2089af3f6b50eff83ee19baf41d8f8949c893a` | clean |
| Law API | `/srv/green-server/seexr-api-law` | `ddb8a25f2f4526f2625cac57849593e7166ef667` | `da66acf84c366b491c7adb26e63a4a712b0771a0` | clean |

이 표는 **audit snapshot**이며 최종 시험 release tag가 아니다. 공인시험 시작 전 네 repository 모두 clean이어야 하며 최종 commit/tag를 새 manifest에 다시 기록한다.

현재 KOLAS relevant-source fingerprint:

- Core: `df38c2eab18eaed5d849643ce589523391a4cb02bdb24e11c32dd2599e4888f5`
- Agents: `3dc2a32f7e79bf740a249854284b01072fa41e62209714060eb16237c21d997b`

Agents `86b7f1b`는 일반 Green의 기본 alias를 바꾸지 않고 KOLAS 전용 배포에서만 dated model snapshot을 env로 pin할 수 있는 경로를 추가했다.

## 3. KOLAS 호출 경로

현재 KOLAS harness의 SUT base URL은 다음과 같다.

`https://api.seexr.dev/api`

KOLAS client는 다음 순서로 호출한다.

1. `POST /auth/login` 또는 token/refresh 인증
2. 필요 시 `GET /agents`
3. `POST /chat/sessions`
4. `POST /agents/risk-assessment/runs`
5. `GET /agents/runs/{runId}/events`
6. durable SSE terminal event에서 최종 content 수집

### 3.1 Session 생성

시험 세션은 다음 성격으로 생성된다.

- `agentId = risk-assessment`
- `surface = risk_assessment_workspace`
- title = `KOLAS {case_id}`
- `projectId`는 지정하지 않음

따라서 정상 KOLAS 시험에서는 project instruction 및 project source context를 사용하지 않는 것이 의도된 상태다.

### 3.2 Run request의 고정 context

현재 official runtime이 고정하는 값:

| 필드 | 값 |
|---|---|
| `agent_id` | `risk-assessment` |
| `protocol` | `v2` |
| `modelMode` | `fast` |
| `reasoningStyle` | `balanced` |
| `riskAssessmentMethod` | `빈도강도법 5x4` |
| user language | `ko` |
| timeout | `180s` |
| max retries | `3` |
| retry backoff | `0.5s` exponential, cap 5s |
| SUT concurrency | `6` |

`modelMode=fast`는 OpenAI API의 `service_tier=fast`가 아니다. SEEXR 내부에서 `risk-assessment`를 `quick-fast-v1.0.0` workflow로 routing하는 제품 설정이다.

## 4. KOLAS 입력 범위

KOLAS 메시지는 다음 형태로 생성한다.

- 공정
- 선택적으로 세부공정
- 선택적으로 설비
- 선택적으로 물질/자재
- “명시되지 않은 설비·물질은 임의로 입력 사실로 간주하지 말라”는 고정 문구

시험에서는 다음을 전송하지 않는다.

- GT 위험요인
- GT 사고분류
- GT 감소대책
- GT 법규
- 사진/attachment
- `deviceContext`
- `projectId`
- project source scope
- object focus target

## 5. Core가 추가하는 서버측 context

클라이언트 payload만 같다고 SUT input이 완전히 같은 것은 아니다. Core는 authenticated user와 session 상태를 조회하여 다음 context를 추가할 수 있다.

### 5.1 User saved instruction — Critical

Core는 시험 계정의 저장된 user instruction을 읽어 Agents에 전달한다.

Agents는 이 instruction을:

- 위험성평가 prompt personalization에 삽입할 수 있고,
- 위험성평가 방법/사고사례 포함 여부와 같은 bounded policy decision에도 사용할 수 있다.

저장 user/project instruction이 하나라도 존재하면 `riskPolicyDecisionAgent`가 추가 호출될 수 있다. 해당 agent는 현재 `openai/gpt-4.1-mini`다.

**공인시험 목표 상태:**

- dedicated evaluation account 사용
- user saved instruction = 빈 문자열
- SHA-256(empty UTF-8) = `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- 시험 직전 API 또는 DB의 비밀이 아닌 검증 절차로 empty 상태 확인
- run manifest에 content 자체 대신 `is_empty=true`와 hash 기록

2026-10-11 현재 내부 rehearsal 계정을 API로 검사한 결과 Saved Instruction은 **NON_EMPTY**였고, 내용은 보존/출력하지 않은 채 SHA-256 `cdbc9181ebaa959ae0b2e237b8b4fd1163a09ff542fdd546ee69a2ad5a7c0bad`만 기록했다. 따라서 이 계정은 공식시험에 사용할 수 없다. evaluator preflight는 이제 official live mode에서 이 상태를 자동 FAIL 처리한다. 최종 시험에는 별도의 empty-instruction 전용 계정이 필요하다.

### 5.2 Project instruction

KOLAS session 생성 시 `projectId`를 보내지 않는다. 따라서 최종 시험에서는 다음을 검증한다.

- session `projectId = null`
- project instruction = not applicable / empty
- project source scope = absent

### 5.3 Application preference

KOLAS run payload가 `reasoningStyle=balanced`를 명시하므로 일반 UI의 마지막 reasoning preference에 의존하지 않도록 설계되어 있다. 다만 최종 dry-run에서 effective context가 `balanced`인지 manifest/event로 재확인한다.

### 5.4 Device/location/weather context

KOLAS payload는 `deviceContext`를 전송하지 않는다. 현재 Core의 EnvironmentContextService는 device context가 없으면 환경 context를 생성하지 않으므로 다음이 목표 상태다.

- 위치 미사용
- 날씨 미사용
- client timezone/location inference 미사용

## 6. 실행 workflow

`modelMode=fast`는 Core에서 `quick-fast-v1.0.0`으로 고정 routing된다.

현재 workflow의 주요 단계는 다음과 같다.

1. normalize input / policy decisions
2. photo analysis — 사진이 있을 때만 의미 있음
3. work-context classification
4. RA candidate retrieval
5. contextual candidate generation — environment context가 있을 때만
6. candidate-scope validation
7. risk draft generation
8. risk verification
9. risk evidence application
10. legal-basis verification
11. accident-case retrieval — 요청 시에만
12. deterministic formatting

KOLAS 표준 입력에는 사진·deviceContext·projectId가 없고 accident-cases explicit include 요청도 없다. 시험 전용 계정의 saved instruction을 empty로 고정하면 policy decision은 application fallback으로 해결되어 별도 policy LLM 호출도 발생하지 않는 것이 목표 실행 경로다.

## 7. 위험성평가 후보 검색 의존성

quick-fast는 `riskAssessmentDbTool`을 통해 다음 API에 후보를 요청한다.

- effective candidate URL: `https://api.seexr.dev/ra`
- Green nginx: `/ra/` → `localhost:5030`
- repository: `agent-api-ra`
- search mode: semantic + lexical + structured hybrid search
- workflow request limit: `40`, page `1`

현재 RA 검색 서비스의 코드 기본값이며 환경에서 별도 override가 확인되지 않은 값:

| 설정 | 값 |
|---|---|
| embedding model | `text-embedding-3-large` |
| embedding dimensions | `1536` |
| embedding timeout | `15000ms` |
| RRF semantic weight | `0.45` |
| RRF lexical weight | `0.35` |
| RRF structured weight | `0.20` |
| `DB_SYNCHRONIZE` | default `false` |

현재 API-visible candidate state:

- row count: `6,443`
- first ID: `1`
- last ID: `6,443`
- embedding populated: `6,443 / 6,443`
- embedding model: `text-embedding-3-large`
- embedding version: `risk-search-v1`
- visible canonical row SHA-256: `8d25e2b57701bc97aa61331f55f170655ec52950c555563ebfc8dba3f6f1a493`

위 hash는 API가 반환하는 다음 필드를 ID 순으로 canonical JSON화해 계산한 audit fingerprint다.

`id, process, subProcess, equipment, material, hazard, accidentType, riskLevel, controlMeasure, legalBasis`

**주의:** embedding vector 자체는 API-visible hash에 포함되지 않는다. semantic ranking 재현을 위해 공인 freeze 시 DB 관리자 경로에서 embedding vector/model/version을 포함한 별도 snapshot hash 또는 read-only DB snapshot을 만들어야 한다.

## 8. 법규 검색 의존성

quick-fast의 legal-basis verification은 Agents에서 Core의 `/api/law/search`를 호출하고, Core가 별도 Law API에 proxy한다.

관련 소스 repository는 `seexr-api-law`다. 법규 DB 내용은 시간이 지나며 갱신될 수 있으므로 secondary 법규 관련 지표와 최종 XML은 code commit만으로 재현되지 않을 수 있다.

공인 freeze 시 최소 다음을 고정한다.

- Law API repository commit/tag
- effective `LAW_API_BASE_URL`의 비밀이 아닌 endpoint identity
- law DB snapshot 시각
- `laws`, `law_articles` 등 평가 관련 테이블 row count
- canonical content hash 또는 read-only snapshot hash
- 시험기간 자동 scraping/update 중지 여부

2026-10-11 live DB에서 `laws=17`, `law_articles=2,861`, `law_files=323`을 확인했다. 다만 row 전체 content를 포함한 canonical snapshot hash는 현재 도구 보안경계에서 직접 추출하지 않았으므로 최종 운영자-side snapshot 단계로 `PENDING`이다.

## 9. API schema/versioning

현재 KOLAS harness와 SUT 사이의 실질적 API 계약은 다음과 같다.

| Interface | Version/contract |
|---|---|
| agent protocol | `v2` |
| execution profile | `quick-fast-v1.0.0` |
| risk method | `빈도강도법 5x4` |
| final content | `<risk_assessment>...</risk_assessment>` XML |
| durable result transport | SSE `/agents/runs/{runId}/events` |
| generated-risk unit | `./items/item` |

최종 freeze에서는 OpenAPI 전체가 아니라 시험에 사용되는 endpoint request/response schema와 parser contract의 hash를 별도 manifest에 포함한다.

## 10. Runtime 및 package dependency

2026-10-11 audit host:

- Node.js `v23.11.1`
- npm `11.10.1`

중요 package-lock SHA-256:

| Component | package-lock SHA-256 |
|---|---|
| Core | `b0cd5e227a2460637871e33b59e5d1a453dd2a3c1caf37887d1c96554753307a` |
| Agents | `46b636cc21d7de09b2cd314912c5c6b70b3db1a7dfcd65f2fb327f375d58d372` |
| RA API | `25c8b6da5e0f0ac04831316097eece54321f92de6719a5265413e7315016726f` |
| Law API | `693784dc44ca3746e56e865117c0067f8b6880b24b7f64a3ca42c9f8261c5cd2` |

Agents 주요 resolved package:

- `@mastra/core 1.57.0`
- `mastra 1.23.0`
- `zod 4.3.6`

Core 주요 resolved package:

- `@nestjs/core 11.1.24`
- `typeorm 0.3.30`
- `pg 8.23.1`

공인시험에서는 package-lock과 Node/npm runtime을 함께 freeze한다.

## 11. 현재 Green 환경을 최종 공인환경으로 사용하면 안 되는 이유

2026-10-11 감사 시 Green에는 다음 개발 프로세스가 존재했다.

- Agents: `mastra dev` watcher
- Core: `nest start --watch`
- RA API: 개발 watch 프로세스와 별도 dist process가 존재

이는 소스가 변경될 때 실행상태가 자동 변경될 수 있는 개발형 환경이다. 또한 Core repository에는 비관련 untracked `apple-root-certs/`가 존재한다.

따라서 현재 `api.seexr.dev`는 **engineering/audit candidate**로만 보고, 공인시험은 다음 중 하나로 고정해야 한다.

1. dedicated immutable KOLAS deployment, 또는
2. clean tagged production release를 사용하는 Blue deployment

어느 endpoint를 사용할지는 시험기관 협의와 최종 운영계획에서 정하되, 시험 시작 이후에는 배포 변경을 금지한다.

## 12. SUT Freeze Gate

공인시험 직전 아래를 모두 PASS해야 한다.

- [ ] 네 SUT repository clean
- [ ] 네 repository HEAD가 승인 tag/commit과 일치
- [ ] Core/Agents relevant source fingerprint 기록
- [ ] package-lock hash 기록
- [ ] immutable/non-watch deployment 확인
- [ ] evaluation account user instruction empty + hash 확인
- [ ] session projectId null 확인
- [ ] deviceContext/attachments/project sources absent 확인
- [ ] RA visible content hash 재계산
- [ ] RA embedding 포함 snapshot identity 생성
- [ ] Law DB snapshot identity 생성
- [ ] effective non-secret env manifest 생성
- [ ] endpoint health/smoke PASS
- [ ] 시험 시작 후 deployment/DB update freeze 적용

## 13. 미해결 Decision / Gap

| ID | 중요도 | 항목 | 현재 상태 |
|---|---|---|---|
| `GAP-SUT-002` | Critical | Green dev/watch deployment는 immutable하지 않음 | final endpoint/deployment 필요 |
| `GAP-SUT-003` | Critical | 현재 내부 rehearsal 계정 Saved Instruction이 NON_EMPTY | official preflight가 자동 차단; 별도 empty-instruction 계정 필요 |
| `GAP-SUT-004` | Critical | RA embedding vector 포함 DB snapshot identity 없음 | snapshot/hash 필요 |
| `GAP-SUT-005` | High | Law DB snapshot identity 없음 | snapshot/hash 필요 |
| `GAP-SUT-006` | High | Core repo에 untracked `apple-root-certs/` 존재 | 최종 release는 fully clean 필요 |
| `DEC-SUT-001` | Critical | 최종 시험 endpoint: dedicated KOLAS vs clean Blue release | 시험 전 확정 |
| `DEC-SUT-002` | High | 법규 DB를 primary SUT freeze 범위에 포함하는 상세수준 | secondary metric 범위와 함께 확정 |

## 14. HWP 반영 지시

본 문서는 최종 HWP **붙임 1. 시험방법 및 시험대상 시스템 명세서**의 SUT 부분에 사용한다.

필수 표:

- SUT 구성요소 및 repository version
- 시험 API path/context
- 외부·stateful dependency 목록
- 시험계정/context freeze 항목
- 공인시험 전 SUT Freeze Gate
