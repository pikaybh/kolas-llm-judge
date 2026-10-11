# KOLAS 시험 재현 실행 가이드

- 문서 ID: `KOLAS-DOC-010`
- 버전: `0.1-review`
- 상태: `REVIEW`
- 기준일: `2026-10-11`
- 대상: 시험기관 재현 담당자 / 내부 시험 운영자
- Official entrypoint: `kolas-llm-judge official-live`
- Official runtime: `configs/official_runtime_v1.yaml`

> 재현 패키지는 **① clean evaluator code checkout, ② 보안 GT data package, ③ 시험용 credentials**의 세 부분으로 구성한다. Git 저장소만 clone하면 proprietary GT 원본과 scenario JSONL은 의도적으로 포함되지 않으므로, 세 부분이 모두 준비되어야 end-to-end official run이 가능하다.

## 1. 재현 패키지 구성

### 1.1 Code package

Repository:

```text
pikaybh/kolas-llm-judge
```

필수 tracked 항목:

- `src/kolas_llm_judge/`
- `configs/official_runtime_v1.yaml`
- `configs/ajqg_seed_v1.yaml`
- `configs/ajqg_gate_v1.yaml`
- `configs/rubric_binary_v1.yaml`
- `prompts/judge_binary_v1.md`
- `data/cases/dataset_manifest.json`
- `data/raw/PROVENANCE.md`
- `pyproject.toml`
- `uv.lock`

현재 dependency identity:

| Artifact | SHA-256 |
|---|---|
| `pyproject.toml` | `f826d884f7e0c0dbe0c1fc156c3e9030ac13e98b63e6579a74cf24b18aab39d5` |
| `uv.lock` | `59502e93ca708512472ab858e78d22e3e4f06f5a8de63ddf9e51c8d3475c5c6f` |
| `.env.example` | `3c82cb21e47b3c458570bc5bc67db6ac814bf87ccbac4bfd9f3ad445d9e3c3f9` |

Python requirement: `>=3.12`

### 1.2 Secure GT package

Git에서 제외되는 proprietary data:

```text
data/raw/kolas_v7_73_test.csv.bz2
data/cases/scenarios_v1.jsonl
```

시험기관에는 별도 승인된 보안 전달경로로 제공한다.

검증값:

| Artifact | Expected |
|---|---|
| raw rows | `843` |
| raw SHA-256 | `b76c9efa718a0429f587b311d9e6e1d2107bf13101b0f91bc02a69e695ad142a` |
| scenarios | `425` |
| references | `843` |
| scenario SHA-256 | `2cdc1e8b9e05766d29790965bcf09c4015662daf8c70571209bccb4a15ee419c` |

`official_runtime`과 `dataset_manifest.json`이 이 identity를 다시 검증한다.

### 1.3 Credential package

Credential은 Git/HWP/run artifact에 포함하지 않는다.

필요한 secret은 별도 보안채널로 provisioning한다.

- OpenAI Judge credential: `OPENAI_API_KEY`
- SEEXR 전용 non-admin 시험계정:
  - `SEEXR_EMAIL`
  - `SEEXR_PASSWORD`

공식 장시간 시험은 refresh/relogin 가능한 email/password 방식을 사용한다. static `SEEXR_API_TOKEN`은 development/smoke 용도로만 취급한다.

## 2. Clean-room 설치

### 2.1 새 작업 디렉터리 확보

공식 재현은 기존 개발 작업복사본보다 **새 clone 또는 동일 commit의 깨끗한 archive**를 권장한다.

예시:

```bash
git clone <APPROVED_REPOSITORY_URL> kolas-llm-judge
cd kolas-llm-judge
git checkout <APPROVED_KOLAS_COMMIT_OR_TAG>
git status --porcelain
```

마지막 명령의 출력은 비어 있어야 한다.

현재 운영 서버 작업복사본에는 보존 중인 untracked `docs/lab_handoff/`가 있어 `doctor --official`의 clean-worktree 조건을 통과하지 않는다. 이 폴더를 삭제하거나 변경하지 않고, clean-room 시험은 새 clone을 사용한다.

### 2.2 Python 환경 설치

`uv`를 준비한 뒤:

```bash
uv sync --frozen
```

`uv.lock`과 불일치하는 dependency 재해석을 허용하지 않는다.

### 2.3 GT 배치

보안 package에서 받은 두 파일을 정확한 경로에 배치한다.

```text
data/raw/kolas_v7_73_test.csv.bz2
data/cases/scenarios_v1.jsonl
```

파일명만 맞추지 말고 hash를 확인한다.

```bash
sha256sum data/raw/kolas_v7_73_test.csv.bz2
sha256sum data/cases/scenarios_v1.jsonl
```

### 2.4 Secret 설정

```bash
cp .env.example .env
```

`.env`에는 credential만 실제 값으로 채운다. official mode의 model, concurrency, chunk size, SUT method/mode 등의 시험조건은 `configs/official_runtime_v1.yaml`이 우선하며 CLI/.env override를 허용하지 않는다.

`.env`는 `.gitignore` 대상이다.

## 3. 실행 전 preflight

### 3.1 Offline preflight

진단용:

```bash
uv run kolas-llm-judge doctor --official
```

`--require-ready`가 없으면 `NOT READY` 항목이 있어도 명령 자체는 exit code 0일 수 있다. 자동화/승인 판정에는 다음을 사용한다.

```bash
uv run kolas-llm-judge doctor --official --require-ready
```

주요 검사:

- 425 scenarios / 843 references
- scenario SHA-256
- required files
- official runtime validation
- evaluator Git HEAD
- evaluator clean worktree
- SUT Core/Agents relevant source fingerprint
- Judge model/pipeline/concurrency
- SUT method contract
- credential 존재 여부

### 3.2 Live preflight

```bash
uv run kolas-llm-judge doctor --live --official --require-ready
```

추가 검사:

- 전용 SEEXR 계정 로그인
- renewable auth mode
- authenticated Core API call
- `risk-assessment` agent 존재/활성 여부
- evaluation account Saved Instruction empty — 원문은 기록하지 않고 empty 여부 + SHA-256만 사용
- evaluation account AI token allowance available

현재 내부 rehearsal 계정은 allowance는 PASS지만 Saved Instruction이 NON_EMPTY여서 이 gate에서 `NOT READY`가 된다. `official-live`도 내부적으로 같은 doctor gate를 실행하므로 우회해 공식 run을 시작할 수 없다.

OpenAI credential의 실제 provider 인증은 이어지는 AJQG 호출에서 검증된다.

## 4. Official one-command execution

공식 실행:

```bash
uv run kolas-llm-judge official-live
```

공식 모드는 다음 override를 허용하지 않는다.

- case 일부 실행
- AJQG skip
- case/SUT concurrency CLI override
- 개발용 runtime configuration override

실행 순서:

```text
official runtime validation
→ preflight
→ AJQG (2 repeats)
→ 425-case SUT + Boolean Judge evaluation
→ SUT source end fingerprint
→ deterministic report
→ final status
→ SHA-256 seal
→ self-verification
```

AJQG가 PASS하지 않으면 SUT 본시험을 시작하지 않는다.

## 5. Run ID 및 ordering

Official run ID 규칙:

```text
<UTC YYYYMMDDTHHMMSSZ>-official-live-<8-hex random suffix>
```

예:

```text
20260914T035752Z-official-live-f573f39b
```

run ID는 각 시험을 전역적으로 구분하기 위해 의도적으로 unique하며 동일 입력에서 동일 ID를 재생성하는 deterministic ID가 아니다.

반면 case processing input order는 frozen `scenarios_v1.jsonl` 순서를 기준으로 한다. 각 SUT 요청의 `clientRequestId`는 다음 두 값을 사용한 UUIDv5로 결정적으로 생성한다.

```text
evaluation_run_id + case_id
```

같은 run/case의 create-run retry는 동일 request ID를 사용한다.

## 6. Case별 자동 보존 artifact

각 case는 다음 checkpoint를 독립적으로 보존한다.

```text
runs/<RUN_ID>/cases/<CASE_ID>/
  sut.json
  parsed.json
  binary_judge.json
  result.json
  error.json              # 실패 시
```

### `sut.json`

- request message
- SUT final content
- SSE events
- session/run ID
- elapsed time
- create-run attempts
- stream reconnect count
- retry log
- auth recovery diagnostic

### `parsed.json`

- parsed risk assessment
- deterministic schema/range/score checks

### `binary_judge.json`

- Boolean match matrix
- selected diagnostic matches
- quality/safety decisions
- per-call response metadata
- case metrics

### `result.json`

- scenario input identity
- reference/generated counts
- deterministic result
- final case metrics
- SUT/Judge execution summary

기존 checkpoint가 있으면 완료 stage를 재사용할 수 있어 장시간 실행의 resume를 지원한다.

## 7. 실패 및 retry 증적

실패 시 `error.json`에 최소 다음이 기록된다.

- failed stage
- failure class
- failure reason
- exception type/message
- failure timestamp

자동 failure class:

- `sut_non_completion`
- `evaluator_failure`
- `infrastructure_failure`

SUT의 create-run retry / SSE reconnect 정보는 `sut.json`에도 보존한다.

## 8. Run-level artifact

정상/비정상 여부와 무관하게 가능한 범위에서 다음을 남긴다.

```text
runs/<RUN_ID>/
  preflight.json
  qualification/
    summary.json
    control_results.csv
  manifest.json
  completion.json
  final_status.json
  report/
    summary.json
    case_metrics.csv
    failures.csv
  verification.json
  run_seal.json
  cases/...
```

### `manifest.json`

다음을 포함한다.

- evaluation Git HEAD 및 dirty flag
- dataset SHA-256
- evaluator source-tree identity
- prompt/rubric/runtime/dependency hashes
- Judge configuration
- parallel runner configuration
- SUT evaluation identity
- SUT Core/Agents source fingerprint
- AJQG summary SHA-256
- selected case IDs

Credential/token/password는 저장하지 않는다.

## 9. Source stability

시험 시작 시 Core/Agents relevant source fingerprint를 저장하고, 평가 종료 후 다시 계산한다.

공식 candidate에서 source가 시험 도중 바뀌면 procedure validity를 인정하지 않는다.

주의: 현재 source fingerprint는 Core/Agents code를 직접 다룬다. Phase 2에서 확인한 RA retrieval DB와 Law DB 같은 stateful dependency의 최종 snapshot identity는 공인 시험 release freeze 전에 별도로 manifest에 확정해야 한다.

## 10. 최종 report

프로그램이 자동으로 다음을 계산한다.

- SUT completion rate
- Hazard Semantic Identification Recall
- supplementary hazard identification KPI
- reference risk coverage diagnostic
- accident classification agreement
- mitigation appropriateness/actionability/specificity
- legal basis presence/relevance
- unsafe advice rate
- critical safety error rate
- schema/range/score deterministic checks
- latency/retry/Judge usage statistics

LLM이 최종 metric 값을 직접 산출하지 않는다.

## 11. Seal 및 검증

`run_seal.json`은 run directory 내 artifact들을 path/size/SHA-256으로 정렬하여 root digest를 생성한다.

검증:

```bash
uv run kolas-llm-judge verify <RUN_ID>
```

검증기는 다음을 탐지한다.

- missing artifact
- unexpected artifact
- file content/size mismatch
- seal internal root mismatch
- current artifact root mismatch

`official-live`는 종료 과정에서 seal과 self-verification을 자동 수행한다.

## 12. Example run

보존된 development example:

```text
runs/20260914T035752Z-official-live-f573f39b
```

이 run은 **공식 KOLAS 결과가 아니라 development example**이다.

- selected: 10
- completed: 10
- failed: 0
- SUT source stable: true
- procedure valid: true
- seal verified: true
- final status: `DEVELOPMENT_COMPLETE`
- primary semantic recall: 17/21 = 80.9524%

이 예시는 실행 artifact 구조와 seal/manifest 형식을 확인하는 용도로만 사용한다. `runs/`는 production response를 포함할 수 있으므로 Git에는 배포하지 않는다. 외부기관에는 필요 시 민감정보 검토 후 별도 evidence package로 제공한다.

Example artifact hashes:

| Artifact | SHA-256 |
|---|---|
| `manifest.json` | `180367a0d0e876949270154e6461ece0a9b61fc4277e63916d64912c32b67e68` |
| `completion.json` | `d52322b1558176d742c426e81e63e0739e99155249fb4c868fc7dd88b98de0f1` |
| `final_status.json` | `27cf2197bfed6780064e2c08c8f1fe483eadca15c68616572fbc430fee9cfb53` |
| `report/summary.json` | `7f619fc266426e4155aa57bab3408ac9473e32f950053c94ae2429bc85d0c0ef` |
| `run_seal.json` | `95815937685e4f3c48f5a80794d786956476a2549e574d34aa32976ef52f099d` |
| `verification.json` | `187a69148a95d53528c4fce1d7a97ca7c33d357060a29c9fe8c81c05e4051ee9` |

## 13. 시험 당일 운영 체크

1. 승인된 commit/tag의 새 clone인지 확인
2. `git status --porcelain` empty 확인
3. secure GT 두 파일 배치 및 SHA-256 확인
4. 시험용 `.env`를 보안채널에서 설정
5. `uv sync --frozen`
6. `doctor --live --official --require-ready` PASS
7. `official-live` 시작
8. AJQG PASS 확인
9. 425 cases 완료 상태 확인
10. SUT source stable 확인
11. `procedure_valid=true` 확인
12. final seal verification PASS 확인
13. run directory read-only 보존/복사
14. `run_seal.json` root hash를 시험기록에 기재

## 13.1 2026-10-11 clean-room rehearsal

Fresh clone + secure GT 배치 + `uv sync --frozen` + integrity verification + offline preflight를 수행했다. 상세 evidence는 `CLEAN_ROOM_REHEARSAL_20261011.md`를 참조한다.

- offline reconstruction: PASS
- fresh-clone regression: 18/18 PASS
- live clean-room reproduction: credential/final SUT freeze 문제로 BLOCKED
- final sign-off: NOT YET

## 14. 현재 미완료 운영조건

2026-10-11 기준 아래는 코드를 더 구현해야 하는 문제가 아니라 **최종 공인시험 환경에서 완료해야 할 운영 항목**이다.

- 유효한 OpenAI 시험 credential provisioning 및 시험 직전 AJQG 재실행
- final SUT release의 clean commit/tag 및 dated-model snapshot env 확정
- dedicated evaluation account의 Saved Instruction empty 상태 확정
- RA retrieval DB embedding 포함 snapshot identity 확정
- Law DB snapshot identity 확정
- 시험기관 clean-room에서 실제 end-to-end 재현 drill 수행

따라서 본 문서는 재현 절차와 프로그램 package를 정의하지만, 외부기관 clean-room 성공을 이미 완료했다고 주장하지 않는다.
