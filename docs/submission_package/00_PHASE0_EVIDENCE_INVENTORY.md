# Phase 0 Evidence Inventory — 기존 KOLAS 구현·GT·실행 증적 재감사

- 문서 ID: `KOLAS-EVIDENCE-000`
- 버전: `0.2`
- 상태: `REVIEW`
- 감사 기준일: `2026-10-11`
- Canonical repository: `/home/pikaybh/Sandbox/kolas-llm-judge`
- 목적: KOLAS 제출 패키지 작성 전에 기존 구현·데이터·실행기록을 사실 기준으로 식별하고, 이후 문서가 참조할 Evidence ID를 부여한다.

> 주의: 이 문서는 **공인시험 성적서가 아니다.** 과거 개발/검증 run과 현재 구현을 제출 준비 관점에서 재감사한 내부 증적 등록부이다.

## 1. 감사 결론

1. `KOLAS_RA_GT v1.0.0`의 현재 로컬 canonical **processing source** 및 scenario 파일은 manifest에 고정된 SHA-256과 **일치**한다. Legacy 원본 XLSX bytes는 현재 로컬에서 미확보다.
2. 데이터셋 수량은 **843 raw rows / 425 scenarios / 843 references**로 manifest와 일치한다.
3. 현재 official runtime의 dataset/prompt/rubric/evaluator source hash 검증은 **PASS**한다.
4. KOLAS Judge는 `gpt-5.6-sol`, `reasoning_effort=medium`, Structured Output을 명시한다. 반면 `temperature`, `top_p`, `max_output_tokens`, `service_tier`는 현재 요청에서 명시하지 않는다.
5. SEEXR의 `modelMode=fast`는 OpenAI API의 Fast processing tier가 아니라 **SEEXR 내부 실행 프로필 `quick-fast-v1.0.0`**을 의미한다. 두 용어는 최종 문서에서 분리해야 한다.
6. 2026-09-09의 425-case `official-live` 명령 실행은 419/425 SUT completion이었으나 evaluator failure 1건 때문에 `procedure_valid=false`, `status=INVALID`이다. 따라서 공인 성능 결과로 사용할 수 없고 개발/분석 source evidence로만 사용한다.
7. 위 425-case run의 seal은 1,695 artifacts에 대해 검증되었으므로, 해당 run 내부 산출물의 **사후 무결성 증적**으로는 사용할 수 있다.
8. 당시 SUT source는 run 중에는 stable했지만 Core와 Agents 모두 relevant working tree가 dirty였다. 따라서 당시 SUT를 Git commit만으로 완전 복원할 수 없다. 향후 시험기관 제출용 SUT는 **clean commit/tag로 새 freeze**해야 한다.
9. 현재 GT provenance는 원본 XLSX→CSV 전송/변환 계보까지만 증명한다. **843 reference hazard 각각의 안전 근거 출처(source provenance)는 존재하지 않는다.** 이번 제출 준비의 가장 큰 GT gap이다.
10. GT 자체는 연구실 구성원들이 이미 검토·검증한 데이터셋이다. Judge의 human calibration은 이 GT 검증과 별개의 evaluator 검증 경로다.

## 2. Evidence Register

### 2.1 Ground Truth / Dataset

| Evidence ID | 대상 | 위치 | 식별값/상태 | 제출 관점 판단 |
|---|---|---|---|---|
| `EV-GT-001` | Dataset manifest | `data/cases/dataset_manifest.json` | SHA-256 `e7679fabc39f6c6abb7eb53fdc72a9374deb8b0e64add9cdff4e89ec1cfddc2a` | canonical metadata |
| `EV-GT-002` | Normalized raw GT | `data/raw/kolas_v7_73_test.csv.bz2` | SHA-256 `b76c9efa718a0429f587b311d9e6e1d2107bf13101b0f91bc02a69e695ad142a`; 843 rows | proprietary/ignored; 제출 패키지에 별도 포함 필요 |
| `EV-GT-003` | Scenario GT | `data/cases/scenarios_v1.jsonl` | SHA-256 `2cdc1e8b9e05766d29790965bcf09c4015662daf8c70571209bccb4a15ee419c`; 425 scenarios / 843 refs | 시험 입력·reference canonical file |
| `EV-GT-004` | 전송/변환 provenance | `data/raw/PROVENANCE.md` | 원본 XLSX 기록 SHA-256 `d12c7d683518b680615e2311f49059ed3f5c439cf6c706afb671b6c7bcafdd4a` | 파일 계보는 있음; 원본 XLSX 바이트는 현재 미발견; hazard별 근거 출처는 없음 |
| `EV-GT-005` | Reference lineage index | `data/cases/gt_lineage_index_v1.csv` | SHA-256 `55c0aa75f8cc0ca542c1fb6755a06ed563f02b0150605a227f2539d907aefbd6`; 843 entries | reference ↔ source_row ↔ case_id, source rows 2..844 완전 커버 |
| `EV-GT-006` | Reference provenance register | `data/cases/gt_provenance_register_v1.csv` | SHA-256 `00b52d389e2afc170c4114ac0308075199beb94d33c725a1beed6b370a679f1c`; 843 entries | hazard 원문 없이 `reference_hazard_sha256`로 content binding; authoritative source unresolved |
| `EV-GT-007` | Provenance audit manifest | `data/cases/gt_provenance_audit_manifest_v1.json` | SHA-256 `ec5bd4f9fded546ac4f2671da5e610688e674193135c9fc1c3b9ef7ac9c3727c` | lineage 843/843; GT 자체는 연구실 구성원 검토를 거쳐 검증 완료; 원작성 source provenance는 별도 추적정보 |
| `EV-GT-008` | Provenance schema | `configs/gt_provenance_schema_v1.yaml` | SHA-256 `58d9ad6b9566b17bc114786b037e0efcd901ba9de316a5241f72fd4c06c03fe2` | source taxonomy/locator/license/expert-validation 필드 규격 |

현재 raw GT 컬럼은 `공정`, `세부공정`, `설비`, `물질`, `유해위험요인`, `사고분류`, `위험 가능성`, `위험 중대성`, `위험성`, `감소대책`, `관련근거(법규)`의 11개다. 별도 `source`, `출처`, `근거문헌` 필드는 존재하지 않는다.


> **2026-10-11 Phase 3 정정:** 최초 Phase 0 문서화 과정에서 `EV-GT-002` raw hash와 `EV-GT-004` original-workbook hash 및 raw header 명칭이 잘못 전사되었다. 본 표는 실제 파일 SHA-256 재계산, `data/raw/PROVENANCE.md`, 초기 Git commit `ca16726`, dataset manifest 및 official runtime을 교차검증해 정정했다. Canonical GT 파일 자체가 변경된 것은 아니다.

### 2.2 Frozen Evaluator / Judge

| Evidence ID | 대상 | 위치 | 확인 내용 |
|---|---|---|---|
| `EV-EVAL-001` | Official runtime | `configs/official_runtime_v1.yaml` | runtime `official-runtime-v1`; current file SHA-256 `1be77e55532324f98d8f2835178a1c02ead325c4f94b4724bda5511d883511e3` |
| `EV-EVAL-002` | Binary prompt | `prompts/judge_binary_v1.md` | official runtime이 prompt SHA를 고정 |
| `EV-EVAL-003` | Binary rubric | `configs/rubric_binary_v1.yaml` | MATCH primary = `same_hazard_mechanism AND context_compatible` |
| `EV-EVAL-004` | Judge implementation | `src/kolas_llm_judge/binary_judge.py` | OpenAI Responses `parse`, structured Pydantic output, `store=False` |
| `EV-EVAL-005` | Evaluator source aggregate hash | `configs/official_runtime_v1.yaml` + validator | expected/actual `0069d7c24a53339b7d586e435547544e8bf8d4a7c52395f730efbffefd76a701` 일치; evaluation-account readiness preflight 강화분 포함; `validate_official_runtime(...)` PASS (2026-10-11) |
| `EV-EVAL-006` | AJQG seed/gate | `configs/ajqg_seed_v1.yaml`, `configs/ajqg_gate_v1.yaml` | official runtime이 SHA로 고정 |
| `EV-EVAL-007` | AJQG hardening summary | `runs/_qualification/20260914-kolas-v1-hardening/summary.json` | SHA-256 `8ecffc8120381fb612b20b318ce916889a71da2005fde9b643515e6b3ac99309`; 104 controls × 2; 376/376 stability; PASS |
| `EV-EVAL-008` | AJQG hardening control rows | `runs/_qualification/20260914-kolas-v1-hardening/control_results.csv` | SHA-256 `f362861e34544dce100d600218ce23f0953e4cb87aa915f980a830e53d3fbf58`; 248 expected Boolean rows |
| `EV-EVAL-009` | AJQG boundary run | `runs/20260909T025259Z-official-live-ca5f3e25/qualification/summary.json` | SHA-256 `958fd53cba792d5e147697cb4b997fa71dbb2219caf49d318b52bb2951fb1a8b`; 375/376 stability; PASS |
| `EV-EVAL-010` | AJQG boundary control rows | `runs/20260909T025259Z-official-live-ca5f3e25/qualification/control_results.csv` | SHA-256 `2e60e30232b088628fc954d4bf23421bc68527b83186223e19ccea398f24c304`; mitigation_specific 1 decision mismatch |
| `EV-EVAL-011` | Current-source fresh AJQG submission evidence | `data/submission/evidence/ajqg_20261011/` | 104 controls ×2, all metrics 1.0000, 376/376 stable, PASS; summary `5ad49cbd...b623`; LF-normalized controls `d58600def63198640101bb740ed3406efe53f06c7203d7a69d41e048b070caf6`; binding `abac8aeefc86112e02e230247c42b3292c780d859c29c6d12b61a09db12354cb` |

Judge 호출에서 코드로 명시되는 값:

| 항목 | 현재 상태 |
|---|---|
| model | `gpt-5.6-sol` 명시 |
| reasoning effort | `medium` 명시 |
| output format | Pydantic Structured Output 명시 |
| store | `false` 명시 |
| request timeout | `180s` 명시 |
| SDK retry | `3` 명시 |
| max concurrency | `12` 명시 |
| temperature | **요청에서 미지정** |
| top_p | **요청에서 미지정** |
| max_output_tokens | **요청에서 미지정** |
| service_tier | **요청에서 미지정** |
| seed | 현재 사용 중인 Responses 호출에 미지정; 2026-10-11 검토한 Responses create schema에서 seed 항목을 확인하지 못함 |

OpenAI 공식 API 문서 확인 기준(2026-10-11):

- GPT-5.6 Sol model: `https://developers.openai.com/api/docs/models/gpt-5.6-sol`
- Responses create API: `https://developers.openai.com/api/reference/resources/responses/methods/create`
- Fast mode: `https://developers.openai.com/api/docs/guides/fast-mode`

공식 문서상 GPT-5.6 Sol은 `medium` reasoning effort를 지원하며, Responses API에는 `temperature`, `top_p`, `service_tier` 등의 요청 필드가 있다. `service_tier=fast`는 OpenAI serving tier이며 SEEXR의 `modelMode=fast`와 무관하다. 현재 Judge 코드가 `service_tier`를 보내지 않으므로, 제출 전 Phase 2에서 명시적 고정 또는 effective tier 기록 방식을 결정해야 한다.

### 2.3 Measurement Program / Runtime

| Evidence ID | 대상 | 위치/값 | 확인 내용 |
|---|---|---|---|
| `EV-SW-001` | KOLAS harness repository | `/home/pikaybh/Sandbox/kolas-llm-judge` | canonical measurement program repository |
| `EV-SW-002` | Python runtime | Python `3.12.3` | 2026-10-11 audit host |
| `EV-SW-003` | uv | `0.8.5` | audit host |
| `EV-SW-004` | lockfile | `uv.lock` | SHA-256 `59502e93ca708512472ab858e78d22e3e4f06f5a8de63ddf9e51c8d3475c5c6f` |
| `EV-SW-005` | project metadata | `pyproject.toml` | SHA-256 `f826d884f7e0c0dbe0c1fc156c3e9030ac13e98b63e6579a74cf24b18aab39d5` |
| `EV-SW-006` | resolved OpenAI SDK | `openai 3.8.0` | 현재 audit environment |
| `EV-SW-007` | OS/kernel | Linux `7.0.0-30-generic`, x86_64 | 현재 audit host; 최종 시험환경은 별도 freeze 필요 |

2026-10-11 focused reproducibility regression test:

- 대상: dataset / official runtime / manifest identity / seal / identification / repeatability freeze / SUT config·retry·auth refresh
- 결과: **25 passed**
- 실행 명령은 Git history 및 본 문서 작성 작업로그에서 재현 가능함.

### 2.4 SUT API / Execution Profile

| Evidence ID | 대상 | 위치 | 확인 내용 |
|---|---|---|---|
| `EV-API-001` | SUT client/auth flow | `src/kolas_llm_judge/sut_client.py` | login + rotating refresh + relogin recovery; session/run/event endpoint 사용 |
| `EV-API-002` | SUT base URL | official runtime | 현재 `https://api.seexr.dev/api`; final accredited endpoint는 release freeze에서 확정 |
| `EV-API-003` | Minimum role | Core global guards + `agents.controller.ts` | dedicated active `Role.USER`; admin role/RBAC 불필요 |
| `EV-API-004` | Session/run ownership | Core `chat.service.ts`, `agent-runs.service.ts` | authenticated user ID로 session/run/event 소유권 강제 |
| `EV-API-005` | AI allowance | Core `SubscriptionAccessGuard` | POST durable agent run은 `assertAiTokenAllowance(userId)` 통과 필요 |
| `EV-API-006` | Token lifetime | Green `.env.local` + auth code | access `15m`, refresh `7d` current effective; final release에서 재확인 |
| `EV-API-007` | Credential revocation | `/auth/logout`, `/auth/devices/{id}`, inactive account | refresh/device session revoke 경로 확인 |
| `EV-API-008` | Current throttle | Core Throttler v6.5.0 + Green env | global 100/60ms current config; login 10/60s; refresh 20/60s |
| `EV-SUT-001` | SUT agent | official runtime | `risk-assessment` |
| `EV-SUT-002` | SEEXR product model mode | official runtime | `fast` → Core에서 `quick-fast-v1.0.0`으로 routing |
| `EV-SUT-003` | reasoning style | official runtime | `balanced` |
| `EV-SUT-004` | RA method | official runtime | `빈도강도법 5x4` |
| `EV-SUT-005` | Current Core relevant source | Core HEAD `279bc052830bca596183ecbe8378dd69d6722f15` | fingerprint `df38c2eab18eaed5d849643ce589523391a4cb02bdb24e11c32dd2599e4888f5`; relevant dirty=false |
| `EV-SUT-006` | Current Agents relevant source | Agents HEAD `86b7f1bfdefad8bac5eeee68e685277cd955f37c` | fingerprint `3dc2a32f7e79bf740a249854284b01072fa41e62209714060eb16237c21d997b`; model snapshot override path 포함 |
| `EV-SUT-007` | RA live embedding coverage | `agent-api-ra` DB audit | 6,443/6,443 embedded; model `text-embedding-3-large`; version `risk-search-v1` |
| `EV-SUT-008` | Law live content counts | `seexr-api-law` DB audit | `laws=17`, `law_articles=2861`, `law_files=323` |
| `EV-API-009` | Current rehearsal account readiness | authenticated API, secret/content 미기록 | Saved Instruction **NON_EMPTY** (SHA-256 `cdbc9181ebaa959ae0b2e237b8b4fd1163a09ff542fdd546ee69a2ad5a7c0bad`) → official preflight FAIL; `tokens_limit=null`, used `96320` → allowance PASS |

**용어 구분:** `SEEXR modelMode=fast`는 제품 내부 workflow 선택값이다. OpenAI API의 `service_tier=fast`와 동일하지 않다.

현재(2026-10-11) quick-fast workflow에서 직접 호출되는 LLM agent들은 주로 `openai/gpt-4.1`이며, 사진·사고사례 단계는 `openai/gpt-4o`다. 하지만 최종 KOLAS 시험에서는 **현재 개발 HEAD가 아니라 시험용으로 freeze한 clean SUT release**의 agent별 모델/config를 다시 manifest로 뽑아야 한다.

### 2.5 Historical SUT Identity — 2026-09-09 full run

| Evidence ID | 대상 | 값 |
|---|---|---|
| `EV-SUT-HIST-001` | Core tracked HEAD | `9725727c285d6ec5594b8d08ef0f401fd9b85610` |
| `EV-SUT-HIST-002` | Agents tracked HEAD | `b7c94b3927a73ae36f5f695dd0c1e174221efe09` |
| `EV-SUT-HIST-003` | Core relevant fingerprint | `a20a3b7df8657638fcd952b7e6ecde7c918568febc861263ebcdf51ceb486ce7` |
| `EV-SUT-HIST-004` | Agents relevant fingerprint | `6954b51a4e49013aafd004cf0c544c4e5d075d4e7b09301eb7ef4438c5ac3f9b` |

당시 두 repository 모두 `relevant_dirty=true`였다. run 종료 시 fingerprint가 시작값과 같아 **run 중 source stability**는 확인됐지만, dirty working tree의 전체 파일 snapshot/patch가 run package에 보존된 것은 아니다. 따라서 이 과거 실행의 SUT는 tracked commit만 checkout해서 byte-for-byte 재구성할 수 없다.

해당 tracked Agents HEAD에서 확인되는 quick-fast 핵심 모델은 다음과 같다.

- `quickFastRiskDraftV1_0_0Agent`: `openai/gpt-4.1`
- `quickFastRiskVerifyV1_0_0Agent`: `openai/gpt-4.1`
- `photoAgent`: `openai/gpt-4o`
- `accidentAgent`: `openai/gpt-4o`

단, dirty 변경이 실제 모델/config에 영향을 주지 않았다고 단정할 수 없으므로 이는 **historical tracked baseline**으로만 기록한다.

### 2.6 Historical Run Artifacts

| Evidence ID | run/artifact | 상태 | 용도 |
|---|---|---|---|
| `EV-RUN-001` | `runs/20260909T025259Z-official-live-ca5f3e25/` | 425 selected; 419 completed; 6 failed; `procedure_valid=false`; `status=INVALID` | 개발 full-run source evidence. 공인 결과로 사용 금지 |
| `EV-INT-001` | 위 run `verification.json` | 1,695 artifacts, seal verified, root `fca11a33df7c5d180fd375596d635182a4565cfffeaa11ca93607c9ba7cdd206` | run 내부 artifact 무결성 증적 |
| `EV-RUN-002` | `derived/20260909T025259Z-official-live-ca5f3e25-identification.json` | broad 795/831; strict semantic 711/831; 12 unjudged | 개발 재분석. metric 정의 구분 필수 |
| `EV-RUN-003` | `derived/repeatability-live-10case-20260914.json` | strict 17/21 vs 16/21; mean 0.7857; reference detection 20/21 stable | strict semantic 반복성 개발 증적 |
| `EV-RUN-004` | `derived/repeatability-live-smoke-20260914.json` | 1-case paired smoke | 소규모 절차 검증 |

`EV-RUN-001`이 INVALID인 직접 사유는 evaluator/infrastructure failure 1건이 존재하기 때문이다. 따라서 파일명에 `official-live`가 포함되어 있어도 공인 성능 결과로 해석하지 않는다.

### 2.7 Credential / Security Boundary

| Evidence ID | 항목 | 상태 |
|---|---|---|
| `EV-SEC-001` | `.env` | `.gitignore`로 제외됨 |
| `EV-SEC-002` | `.env.example` | 변수명만 tracked; secret 값 없음이 원칙 |
| `EV-SEC-003` | canonical raw GT / scenarios / runs / derived | Git ignore 대상; 기관 전달 시 별도 controlled package 필요 |

현재 `.env`에서 사용하는 credential 계열 변수에는 `OPENAI_API_KEY`, `SEEXR_API_TOKEN`, `SEEXR_EMAIL`, `SEEXR_PASSWORD`가 있다. 실제 값은 문서/버전관리/최종 HWP에 기록하지 않고 별도 보안채널로 전달해야 한다.

## 2.8 Reproducibility Runner / Package

| Evidence ID | 항목 | 근거 | 상태 |
|---|---|---|---|
| `EV-REPRO-001` | Official entrypoint | `src/kolas_llm_judge/official_live.py`, CLI `official-live` | preflight→AJQG→425 evaluation→report→seal→verify 자동화 |
| `EV-REPRO-002` | Dependency lock | `pyproject.toml`, `uv.lock` | Python >=3.12; `uv sync --frozen` 절차 정의 |
| `EV-REPRO-003` | Official preflight | `src/kolas_llm_judge/doctor.py` | dataset/hash/git/SUT source/auth/runtime 검사 |
| `EV-REPRO-004` | Per-case checkpoint | `src/kolas_llm_judge/parallel_runner.py` | SUT/parsed/Judge/result/error 자동 보존 |
| `EV-REPRO-005` | Run manifest | `src/kolas_llm_judge/automated_manifest.py` | dataset/code/config/Judge/SUT/source fingerprint 기록 |
| `EV-REPRO-006` | Run seal | `src/kolas_llm_judge/seal.py` | artifact path/size/SHA-256 root + verify |
| `EV-REPRO-007` | Example development run | `runs/20260914T035752Z-official-live-f573f39b` | 10/10 complete, source stable, procedure valid, seal verified; official result 아님 |

## 3. Phase 0 Gap Register

| Gap ID | 중요도 | 발견사항 | 후속 단계 |
|---|---|---|---|
| `GAP-GT-001` | Critical | 843 reference hazard별 근거 source provenance가 없음 | Phase 3 |
| `GAP-GT-002` | Resolved | GT는 연구실 구성원들의 검토를 거쳐 이미 검증된 데이터셋임 | 신규 검증 불필요 |
| `GAP-SUT-001` | Critical | 과거 425-case run의 SUT가 dirty working tree여서 commit만으로 완전 재현 불가 | Phase 2/9에서 clean release 새 freeze |
| `GAP-RUN-001` | Critical | 2026-09-09 425-case run은 `procedure_valid=false` | 승인된 freeze 후 새 full run 필요 |
| `GAP-EVAL-001` | High | Judge가 `temperature`, `top_p`, `max_output_tokens`, `service_tier`를 명시하지 않음 | Phase 2/5에서 명시 또는 provider-default/effective 값 기록 정책 확정 |
| `GAP-EVAL-002` | High | 기존 persisted Judge call metadata가 response ID/model/usage 중심이며 effective service tier·temperature/top_p 전체를 보존하지 않음 | Phase 5/6 |
| `GAP-PKG-001` | Partially resolved | code + secure GT + credential의 3-part 전달 절차는 Phase 6에서 정의됨; 실제 기관 전달 bundle 조립은 미완료 | Phase 8/11 |
| `GAP-API-001` | Medium | 시험기관용 최소권한 credential lifecycle이 아직 공식 문서화되지 않음 | Phase 7 |
| `GAP-HWP-001` | Medium | 기관 제공 공식 HWP 양식/문서번호/수신처/결재정보 미확정 | Phase 10 |

## 4. Phase 0 이후 고정해서 사용할 사실

아래는 후속 문서의 baseline으로 사용할 수 있다.

- Dataset identity: `KOLAS_RA_GT v1.0.0` / `kolas-ra-dataset-v1`
- Dataset size: 425 scenarios / 843 references / 843 source rows
- Canonical scenario SHA-256: `2cdc1e8b9e05766d29790965bcf09c4015662daf8c70571209bccb4a15ee419c`
- Primary metric: `hazard_semantic_identification_recall`
- Primary MATCH: `same_hazard_mechanism AND context_compatible`
- Evaluator pipeline: `binary-checklist-v1`
- Judge model configuration currently frozen in runtime: `gpt-5.6-sol`, reasoning `medium`
- SEEXR test execution mode currently frozen in runtime: product `modelMode=fast`, `reasoningStyle=balanced`, `빈도강도법 5x4`
- `modelMode=fast` ≠ OpenAI `service_tier=fast`
- Existing 2026-09-09 425-case run ≠ accredited final result

## 5. Phase 0 완료 판단

Phase 0의 목적은 기존 자산을 **발견·검증·분류하고 gap을 명시하는 것**이다. 위 Evidence Register와 Gap Register가 생성되었으므로 Phase 0은 완료로 본다. GT source provenance 생성, 전문가 검증, clean SUT freeze, 새로운 full run 등은 후속 Phase의 작업이다.
