# KOLAS 제출용 버전 및 Freeze Manifest

- 문서 ID: `KOLAS-DOC-012`
- 버전: `0.3-draft`
- 상태: `REVIEW`
- 기준일: `2026-10-11`
- Freeze candidate ID: `SEEXR-RA-SUT-RC-2026.10.11.1`
- 최종 release/tag: `{{FINAL_MEASUREMENT_RELEASE_TAG}}`

> 이 문서는 현재 audit snapshot과 최종 freeze 시 채워야 할 필드를 한 곳에 모은다. `PENDING` 항목이 존재하는 동안 공인시험용 최종 manifest가 아니다.

## 1. Measurement Program

| 항목 | 값 | 상태 |
|---|---|---|
| repository | `pikaybh/kolas-llm-judge` | 확인 |
| submission candidate base commit before Phase 8 integrity build | `08e0419` | Phase 8 생성 시점의 committed base; final release 아님 |
| final measurement tag | `{{FINAL_MEASUREMENT_RELEASE_TAG}}` | PENDING |
| official runtime | `official-runtime-v1` | 확인 |
| `configs/official_runtime_v1.yaml` SHA-256 | `1be77e55532324f98d8f2835178a1c02ead325c4f94b4724bda5511d883511e3` | 확인 |
| `sut_client.py` SHA-256 | `45cbc9a94f1f4e7497d4bd55826eaf5a032ab03f33e86494d82126cab4d42e1d` | 확인 |
| Python | `3.12.3` | Phase 0 audit |
| uv | `0.8.5` | Phase 0 audit |
| `uv.lock` SHA-256 | `59502e93ca708512472ab858e78d22e3e4f06f5a8de63ddf9e51c8d3475c5c6f` | Phase 0 audit |

## 2. Dataset / GT

| 항목 | 값 | 상태 |
|---|---|---|
| Dataset ID | `KOLAS_RA_GT` | 확인 |
| version | `1.0.0` | 확인 |
| schema | `kolas-ra-dataset-v1` | 확인 |
| scenarios | `425` | 확인 |
| references | `843` | 확인 |
| source rows | `843` | 확인 |
| original XLSX recorded SHA-256 | `d12c7d683518b680615e2311f49059ed3f5c439cf6c706afb671b6c7bcafdd4a` | 원본 바이트 미발견; 기록값 |
| canonical raw SHA-256 | `b76c9efa718a0429f587b311d9e6e1d2107bf13101b0f91bc02a69e695ad142a` | 확인 |
| scenarios SHA-256 | `2cdc1e8b9e05766d29790965bcf09c4015662daf8c70571209bccb4a15ee419c` | 확인 |
| lineage index SHA-256 | `55c0aa75f8cc0ca542c1fb6755a06ed563f02b0150605a227f2539d907aefbd6` | 843/843 source-row lineage 확인 |
| provenance register SHA-256 | `00b52d389e2afc170c4114ac0308075199beb94d33c725a1beed6b370a679f1c` | 843 entries, raw hazard text 미포함 |
| provenance audit manifest SHA-256 | `ec5bd4f9fded546ac4f2671da5e610688e674193135c9fc1c3b9ef7ac9c3727c` | Phase 3 audit |
| provenance schema SHA-256 | `58d9ad6b9566b17bc114786b037e0efcd901ba9de316a5241f72fd4c06c03fe2` | schema 작성 |
| original-source provenance | `not structured at reference level` | GT 검증 상태와 별개 |
| GT validation status | `validated by research laboratory members` | 기존 검증 완료; 신규 검증 불필요 |
| additional validation package | `N/A` | 기존 GT 검증 사실만 기록; 별도 신규 검증 패키지 미작성 |

## 2.1 Evaluator / Judge freeze

| 항목 | 값 | 상태 |
|---|---|---|
| evaluator source aggregate SHA-256 | `0069d7c24a53339b7d586e435547544e8bf8d4a7c52395f730efbffefd76a701` | frozen |
| official runtime SHA-256 | `1be77e55532324f98d8f2835178a1c02ead325c4f94b4724bda5511d883511e3` | 확인 |
| Judge model | `gpt-5.6-sol` | frozen |
| reasoning effort | `medium` | frozen |
| prompt SHA-256 | `97884ac7d7440b8e3843b0eee357478275871f949d4ef305b5c52a1eb3bad0bf` | frozen |
| rubric SHA-256 | `d6993b9c49a88e4d5389c8d72dde27d750d0880c57d2fd18d38e08ae3ae93a22` | frozen |
| AJQG seed SHA-256 | `f0f11537d77555e55fe5ae143fa92e92ddc631da1d7a1711fe2f070ad38b8586` | frozen |
| AJQG gate SHA-256 | `2ee9934e921fa82b10697d6cf9ffca6e72f151a49159ac3aff7a8b7d17421a6b` | frozen |
| AJQG control suite | `ajqg-controls-v1`, 104 controls, `e0a34a81...e437` | frozen |
| canonical hardening AJQG | 376/376 repeated decisions, gate PASS | 확인 |
| current-source fresh AJQG | 104 controls ×2, all metrics 1.0000, 376/376 stable, PASS | evidence binding `abac8aee...54cb` |
| AJQG summary SHA-256 | `5ad49cbda247ceab93edaf60942ed86f31d32f557fe3403455c99c24aac6b623` | 제출 evidence |
| AJQG submission control results SHA-256 | `d58600def63198640101bb740ed3406efe53f06c7203d7a69d41e048b070caf6` | CRLF→LF normalized submission copy |
| AJQG raw-run control results SHA-256 | `f362861e34544dce100d600218ce23f0953e4cb87aa915f980a830e53d3fbf58` | 원본 `runs/` artifact, 변경 없음 |
| AJQG binding SHA-256 | `abac8aeefc86112e02e230247c42b3292c780d859c29c6d12b61a09db12354cb` | source/runtime/artifact binding |

## 2.2 API access contract (current Green audit)

| 항목 | 값 | 상태 |
|---|---|---|
| current official runtime base URL | `https://api.seexr.dev/api` | final accredited endpoint PENDING |
| test role | `user` | minimum practical role |
| access token lifetime | `15m` | Green effective, final recheck |
| refresh token lifetime | `7d` | Green effective, final recheck |
| refresh policy | rotating/revocable | 확인 |
| run entitlement | AI token allowance required | 확인 |
| session/run isolation | authenticated owner user ID enforced | 확인 |
| endpoint-specific OAuth scopes | not implemented | role/ownership/entitlement model 사용 |
| final institution account | `{{KOLAS_TEST_ACCOUNT_ID}}` | PENDING; secret는 manifest에 기록하지 않음 |

## 2.3 Submission integrity policy

| 항목 | 값 | 상태 |
|---|---|---|
| machine manifest | `data/submission/submission_integrity_manifest_v1.json` | Phase 8 candidate에서 생성 |
| manifest version | `submission-integrity-v1` | 확인 |
| hash algorithm | `SHA-256` | 확인 |
| root algorithm | sorted `path\0sha256\0size\n` records | 확인 |
| integrity report | `docs/submission_package/13_INTEGRITY_MANIFEST.md` | self-reference 방지를 위해 root 대상에서 제외 |
| final HWP/HWPX/PDF | 아직 미생성 | Phase 10/11 직전 final manifest에 추가 |
| final Git tag/release | `{{FINAL_MEASUREMENT_RELEASE_TAG}}` | PENDING |

## 3. SUT Source Snapshot

### 3.1 Core

- repository path: `/srv/green-server/seexr-api-core`
- current candidate HEAD: `279bc052830bca596183ecbe8378dd69d6722f15`
- current candidate Git tree: `91de2c76fa7cb96dc301ebf2e85abc8a560051d9`
- audit state: **NOT fully clean** — untracked `apple-root-certs/` 1건
- package.json SHA-256: `202942b61cfcfb56e51509fc83d45b2b9fc31f4724d41347fe600b85f6fa95eb`
- package-lock SHA-256: `b0cd5e227a2460637871e33b59e5d1a453dd2a3c1caf37887d1c96554753307a`
- relevant source fingerprint: `df38c2eab18eaed5d849643ce589523391a4cb02bdb24e11c32dd2599e4888f5`
- final tag/commit: `{{CORE_FINAL_COMMIT}}` — PENDING

Critical source hashes:

| file | SHA-256 |
|---|---|
| `agents.controller.ts` | `8ee75e4022ce858a3d46e96426a42d59e8a9a352ff95a11430d33ba94e4ab346` |
| `agents.service.ts` | `18f4e0ab7aa39fc22d682fd0f1c8c5d68421a2cba2c77b5b97058313308af476` |
| `agent-runs.service.ts` | `43d340ebf66bc56855e25e5d2fd056a8a250b787793a704542a411edf5920256` |
| `runtime-context.ts` | `9742a03c8237d0275e180f712d829501187b5774680be578281e03b915f78626` |
| `environment-context.service.ts` | `7482a227fcb96555a20cb7f020aa09c404bdabb4ade8b052e4d082f89d896ea1` |
| `law.service.ts` | `1b18b0def4de207fc4e5598c0f7b4dbb3a374bb88f887f7a033aad4531bd8c1b` |

### 3.2 Agents

- repository path: `/srv/green-server/seexr-api-agents`
- current candidate HEAD: `86b7f1bfdefad8bac5eeee68e685277cd955f37c`
- current candidate Git tree: `62f1f1430a258adfed036bc4a815ca94f00e2f87`
- audit state: clean
- package.json SHA-256: `71cbaf0ab3267c5c42bb45310bbda25576ee320ee6fe5b9df570442a261a820f`
- package-lock SHA-256: `46b636cc21d7de09b2cd314912c5c6b70b3db1a7dfcd65f2fb327f375d58d372`
- relevant source fingerprint: `3dc2a32f7e79bf740a249854284b01072fa41e62209714060eb16237c21d997b`
- model snapshot override implementation: Agents commit `86b7f1b`
- final tag/commit: `{{AGENTS_FINAL_COMMIT}}` — PENDING
- `quickFastRiskAssessmentWorkflow.ts` SHA-256: `530a03c2858da98a1c033b378ab349364e477ae7104ac224873e47b8b6b9b464`

### 3.3 RA Search API

- repository path: `/srv/green-server/agent-api-ra`
- audit HEAD: `b400f87ffc483764e8a8857e12c188867425c2b2`
- audit Git tree: `db2089af3f6b50eff83ee19baf41d8f8949c893a`
- audit state: clean
- package.json SHA-256: `4594132ed67f505c87d141d5271cb784c0deac74e473860a1844d4a2b67ec1da`
- package-lock SHA-256: `25c8b6da5e0f0ac04831316097eece54321f92de6719a5265413e7315016726f`
- final tag/commit: `{{RA_FINAL_COMMIT}}` — PENDING

RA stateful data audit:

| 항목 | 값 | 상태 |
|---|---|---|
| API-visible rows | `6,443` | 확인 |
| ID range | `1..6443` | 확인 |
| visible canonical content SHA-256 | `8d25e2b57701bc97aa61331f55f170655ec52950c555563ebfc8dba3f6f1a493` | audit fingerprint |
| embedding model candidate | `text-embedding-3-large` | env override 없음 + source default |
| embedding dimensions candidate | `1536` | source/runtime contract |
| embedding coverage | `6,443 / 6,443` | live DB 확인 |
| embedding version | `risk-search-v1` | live DB 전 행 동일 |
| embedding-vector-inclusive snapshot hash | `{{RA_DB_FULL_SNAPSHOT_SHA256}}` | PENDING |
| DB snapshot timestamp | `{{RA_DB_SNAPSHOT_AT}}` | PENDING |

### 3.4 Law API

- repository path: `/srv/green-server/seexr-api-law`
- audit HEAD: `ddb8a25f2f4526f2625cac57849593e7166ef667`
- audit Git tree: `da66acf84c366b491c7adb26e63a4a712b0771a0`
- audit state: clean
- package.json SHA-256: `87719b1ad5cb76f8b95d3a6f84e26a42d5002eb7a36ebc2249b4f4362cbf6a3c`
- package-lock SHA-256: `693784dc44ca3746e56e865117c0067f8b6880b24b7f64a3ca42c9f8261c5cd2`
- final tag/commit: `{{LAW_FINAL_COMMIT}}` — PENDING
- live DB content counts: `laws=17`, `law_articles=2861`, `law_files=323` — 확인
- law DB full snapshot SHA-256: `{{LAW_DB_SNAPSHOT_SHA256}}` — PENDING
- law DB snapshot timestamp: `{{LAW_DB_SNAPSHOT_AT}}` — PENDING

## 4. SUT API / Execution Configuration

| 항목 | Freeze candidate |
|---|---|
| base URL | `https://api.seexr.dev/api` — engineering candidate only |
| final base URL | `{{FINAL_SUT_BASE_URL}}` — PENDING |
| agent | `risk-assessment` |
| agent protocol | `v2` |
| execution profile | `quick-fast-v1.0.0` |
| product model mode | `fast` |
| reasoning style | `balanced` |
| risk method | `빈도강도법 5x4` |
| SUT timeout | `180s` |
| SUT max retries | `3` |
| SUT retry backoff | `0.5s`, exponential, max 5s |
| SUT concurrency | `6` |
| images | absent |
| device context | absent |
| project ID | absent/null |
| accident cases | omit/not requested target |

## 5. Evaluation Account State

| 항목 | 목표 값 | Freeze evidence |
|---|---|---|
| dedicated non-admin account | yes | `{{EVAL_ACCOUNT_ID_HASH}}` — final institution account PENDING |
| required user saved instruction | empty | expected SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| current internal rehearsal account | **NON_EMPTY — official 사용 불가** | content 미기록; SHA-256 `cdbc9181ebaa959ae0b2e237b8b4fd1163a09ff542fdd546ee69a2ad5a7c0bad` |
| current AI allowance | available | used `96320`, limit `null` |
| official readiness enforcement | automatic | live official doctor가 Saved Instruction + allowance 검사 |
| project | none | run/session manifest |
| project instruction | none | run/session manifest |

계정 이메일, password, access token 등 secret은 이 manifest에 기록하지 않는다.

## 6. Model / Inference Configuration

### 6.1 Normal KOLAS path

| Stage | Model identifier in source |
|---|---|
| work classification | `RISK_MODELS.gpt41`; KOLAS=`openai/gpt-4.1-2025-04-14` |
| candidate scope validation | `RISK_MODELS.gpt41`; KOLAS=`openai/gpt-4.1-2025-04-14` |
| draft | `RISK_MODELS.gpt41`; KOLAS=`openai/gpt-4.1-2025-04-14` |
| verify | `RISK_MODELS.gpt41`; KOLAS=`openai/gpt-4.1-2025-04-14` |

### 6.2 Conditional models

| Stage | Model | Standard KOLAS target |
|---|---|---|
| saved-policy resolution | KOLAS=`openai/gpt-4.1-mini-2025-04-14` | skip when saved instruction empty |
| contextual candidate | KOLAS=`openai/gpt-4.1-2025-04-14` | skip when environment absent |
| photo | KOLAS=`openai/gpt-4o-2024-11-20` | skip |
| accident cases | KOLAS=`openai/gpt-4o-2024-11-20` | skip |

### 6.3 Unset/provider-controlled fields

- temperature: `UNSET`
- top_p: `UNSET`
- seed: `UNSET`
- max output tokens: `UNSET`
- provider reasoning effort: `UNSET`
- provider `service_tier`: `UNSET`

Final model snapshot strategy: **RESOLVED — dedicated KOLAS deployment에서 dated snapshot env pinning**. 일반 Green 기본 alias는 변경하지 않는다. Dated ID Mastra construction 및 실제 provider-call smoke는 모두 PASS했으며 final deployment에서 effective env를 다시 freeze한다.

## 7. Runtime Dependencies

Audit host:

- Node.js: `v23.11.1`
- npm: `11.10.1`

Resolved key packages:

| Component | Package | Version |
|---|---|---|
| Agents | `@mastra/core` | `1.57.0` |
| Agents | `mastra` | `1.23.0` |
| Agents | `zod` | `4.3.6` |
| Core | `@nestjs/core` | `11.1.24` |
| Core | `typeorm` | `0.3.30` |
| Core | `pg` | `8.23.1` |

Final OS/container/image identity: `{{FINAL_DEPLOYMENT_IMAGE_OR_OS_ID}}` — PENDING.

## 8. Evaluator / Judge Identity

| 항목 | 값 |
|---|---|
| Judge pipeline | `binary-checklist-v1` |
| Judge model | `gpt-5.6-sol` |
| reasoning effort | `medium` |
| request timeout | `180s` |
| max retries | `3` |
| max concurrency | `12` |
| prompt SHA-256 | `97884ac7d7440b8e3843b0eee357478275871f949d4ef305b5c52a1eb3bad0bf` |
| rubric SHA-256 | `d6993b9c49a88e4d5389c8d72dde27d750d0880c57d2fd18d38e08ae3ae93a22` |
| evaluator source aggregate SHA-256 | `0069d7c24a53339b7d586e435547544e8bf8d4a7c52395f730efbffefd76a701` |

Judge의 temperature/top_p/max_output_tokens/service_tier는 현재 요청에서 명시하지 않는다. 이 항목은 Phase 5에서 측정시스템 관점으로 최종 처리한다.

## 9. Final Freeze Gate

아래 값이 모두 채워지고 검증되어야 `FINAL/FROZEN` 상태로 변경할 수 있다.

- [ ] `FINAL_MEASUREMENT_RELEASE_TAG`
- [ ] `CORE_FINAL_COMMIT`
- [ ] `AGENTS_FINAL_COMMIT`
- [ ] `RA_FINAL_COMMIT`
- [ ] `LAW_FINAL_COMMIT`
- [ ] 네 repository clean 확인
- [ ] `FINAL_SUT_BASE_URL`
- [ ] immutable deployment identity
- [ ] evaluation account empty-instruction hash
- [ ] RA full DB/embedding snapshot hash
- [ ] Law DB snapshot hash
- [x] model alias/snapshot policy 승인 — dedicated KOLAS deployment snapshot pinning
- [ ] effective non-secret env manifest hash
- [ ] API smoke PASS
- [ ] clean-room dry-run PASS
- [ ] 최종 manifest 자체 SHA-256

## 10. Change-control Rule

Final freeze 이후 아래 중 하나라도 변경되면 같은 SUT version으로 공인 결과를 계속 사용하지 않는다.

- model identifier 또는 snapshot
- prompt/instruction source
- workflow/tool/schema
- Core routing
- RA retrieval code, DB content, embedding, RRF weight
- Law API/DB state가 평가 output에 영향을 주는 변경
- evaluation account instruction
- package lock/runtime
- endpoint deployment artifact

변경 시 새 SUT version을 부여하고 필요한 qualification/repeatability 시험을 다시 수행한다.
