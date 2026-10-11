# Clean-room 재현성 Rehearsal 기록 — 2026-10-11

- Evidence ID: `EV-REPRO-CR-20261011`
- 상태: `PARTIAL / NOT SIGNED OFF`
- 기준일: `2026-10-11`
- Clean-room path: `/tmp/kolas-cleanroom-20261011`
- Clean clone HEAD: `d4465e12109ace5d9405c3e36cd84c2ecc405e71`
- 목적: 기존 evaluator 개발 작업복사본과 분리된 새 clone에서 code/GT/dependency/integrity/preflight를 재구성할 수 있는지 확인

> 결론: **code + secure GT package만으로 clean clone의 설치·데이터 identity·submission integrity·offline deterministic checks까지 재현되었다.** 다만 clean-room에 실제 credential을 전달하지 않았고, 기존 OpenAI credential은 Phase 5 live AJQG에서 401이 확인되었으므로 sample/full live run과 최종 재현 sign-off는 수행하지 않았다.

## 1. 격리환경 준비

새 clone을 별도 `/tmp` 경로에 생성했다.

```text
/tmp/kolas-cleanroom-20261011
```

Clone 직후:

- Git HEAD: `d4465e12109ace5d9405c3e36cd84c2ecc405e71`
- `git status --porcelain`: empty
- proprietary raw GT: 없음
- canonical scenario JSONL: 없음

즉 Git repository만으로 proprietary GT가 암묵적으로 따라오지 않는 설계가 확인되었다.

## 2. Secure GT package 모사

기존 canonical store에서 다음 두 파일만 clean-room의 동일 상대경로에 배치했다.

```text
data/raw/kolas_v7_73_test.csv.bz2
data/cases/scenarios_v1.jsonl
```

결과:

| Artifact | SHA-256 |
|---|---|
| raw GT | `b76c9efa718a0429f587b311d9e6e1d2107bf13101b0f91bc02a69e695ad142a` |
| scenarios | `2cdc1e8b9e05766d29790965bcf09c4015662daf8c70571209bccb4a15ee419c` |

두 파일은 Git ignored이므로 배치 후에도 `git status --porcelain`은 empty였다.

## 3. Dependency 재구성

환경:

- Python `3.12.3`
- uv `0.8.5`

실행:

```bash
uv sync --frozen
```

결과: **PASS**

lockfile 재해석이나 수동 package 추가 없이 환경이 구성되었다.

## 4. Submission integrity 재검증

clean clone에서 실행:

```bash
PYTHONPATH="$PWD:$PWD/src" uv run python tools/build_submission_manifest.py verify
```

결과:

- artifact count: `76`
- missing: `0`
- mismatched: `0`
- internal root: PASS
- current root: PASS
- artifact root:
  `7566872820ed951f05ad6ec18c7dc4aef5ead94dc3a3d35180056f4f8bb6c1ba`

이는 Phase 8 candidate의 파일 내용이 fresh clone + secure GT 배치 후 동일하게 재현됨을 의미한다.

## 5. Offline official preflight

Credential을 clean-room에 전달하지 않은 상태에서:

```bash
uv run kolas-llm-judge doctor --official
```

기술 identity checks는 다음을 포함해 PASS했다.

- project root
- 425 scenarios
- scenario SHA-256
- 843 references
- required config/prompt/docs/lockfile
- evaluator Git HEAD
- clean worktree
- Core relevant source fingerprint
- Agents relevant source fingerprint
- official runtime SHA/version
- Judge model/pipeline/concurrency
- SUT concurrency/retry/mode contract

Credential 관련 항목은 의도대로 FAIL했다.

- `seexr_credentials`: missing
- `seexr_renewable_auth`: missing
- `openai_credentials`: missing

따라서 overall: `NOT READY`

## 6. `--require-ready` 동작 확인

다음 명령으로 acceptance behavior를 별도 검증했다.

```bash
uv run kolas-llm-judge doctor --official --require-ready
```

결과:

- worktree clean: PASS
- credential checks: FAIL
- overall: `NOT READY`
- process exit code: `2`

반면 `--require-ready`가 없는 `doctor --official`은 diagnostic 명령이라 `NOT READY` 상태에서도 exit code `0`일 수 있다.

따라서 자동화된 clean-room sign-off에서는 반드시 `--require-ready`를 사용해야 한다.

## 7. Offline regression

Fresh clone에서 다음 핵심 regression set을 실행했다.

- dataset
- official runtime
- submission integrity
- run seal
- manifest identity

결과: **18/18 PASS**

테스트 종료 후 `git status --porcelain`: empty.

## 8. 기존 환경의 live SUT preflight 교차확인

Secret 값을 출력하거나 이동하지 않고 기존 canonical 작업환경에서:

```bash
kolas-llm-judge doctor --live --official
```

결과 중 live 관련 항목:

- SEEXR credential mode: email/password — PASS
- renewable auth: PASS
- authenticated API request: PASS
- `risk-assessment` agent available: PASS
- OpenAI credential: **presence check PASS**

주의: doctor의 `openai_credentials`는 key 존재 여부를 확인하는 항목이다. Provider가 실제 key를 수락하는지 확인하는 AJQG API 호출과 동일하지 않다.

Phase 5의 2026-10-11 live AJQG 시도에서는 현재 OpenAI credential이 provider에서 **401**로 거부되어 Judge 판정 전 중단되었다. 따라서 “OpenAI live ready”로 해석하지 않는다.

기존 canonical 작업환경은 보존 중인 untracked `docs/lab_handoff/` 때문에 `evaluation_worktree_clean=FAIL`이며 official sign-off 환경으로 쓰지 않는다.

## 9. 이번 rehearsal에서 완료된 것

- [x] 기존 evaluator 작업복사본과 분리된 새 clone 생성
- [x] Git clone만으로 proprietary GT가 따라오지 않음을 확인
- [x] secure GT 두 파일을 별도 배치하는 절차 검증
- [x] GT hash 검증
- [x] `uv sync --frozen` 설치 검증
- [x] submission integrity root 재현
- [x] clean Git worktree 확인
- [x] offline official preflight의 기술 identity 항목 확인
- [x] `--require-ready` non-zero blocking 확인
- [x] fresh clone regression 18/18 PASS
- [x] 기존 환경에서 SEEXR live auth 및 risk agent 상태 교차확인

## 10. 아직 완료되지 않은 것

- [ ] 시험기관/clean-room에 credential package 안전 provisioning
- [ ] clean-room `doctor --live --official --require-ready` PASS
- [ ] 유효 OpenAI credential로 AJQG PASS
- [ ] clean-room sample subset run
- [ ] clean-room 425-case full run
- [ ] 원 official 측정결과와 비교
- [ ] 반복변동 허용기준 최종 확정
- [ ] 작성 작업에 관여하지 않은 제3자/내부 연구자의 독립 재현
- [ ] 최종 reproducibility sign-off

## 11. 현재 blockers

### B1. OpenAI credential

현재 내부 `.env`의 key는 존재하지만 Phase 5 AJQG 실제 API 요청에서 401이었다. 유효 시험용 credential이 필요하다.

### B2. 시험기관 credential provisioning

실제 기관용 전용 `Role.USER` 계정, entitlement, Saved Instruction empty 확인 및 보안 전달이 아직 수행되지 않았다.

### B3. Final SUT freeze

아직 다음이 final 확정되지 않았다.

- final Core/Agents/RA/Law release/tag
- RA embedding-inclusive DB snapshot
- Law DB snapshot
- final SUT base URL
- model snapshot/alias policy

### B4. Independent operator

이번 rehearsal은 제출패키지를 작성하는 에이전트가 실행했다. “작성자가 직접 개입하지 않아도 재현 가능”이라는 Phase 9 최종조건을 충족하려면 작업에 관여하지 않은 연구자 또는 시험기관 담당자가 동일 가이드만 보고 별도 실행해야 한다.

## 12. 문서 보완 결과

이번 rehearsal에서 발견된 실무상 중요한 문서 보완점:

- `doctor --official`은 진단용으로는 유효하지만 readiness 실패 시에도 기본 exit code 0일 수 있다.
- CI/기관 sign-off 명령에는 `--require-ready`를 붙여야 한다.
- code clone과 GT package, credential package는 계속 분리한다.

이 사항은 `10_REPRODUCIBILITY_GUIDE.md`에 반영한다.

## 13. 판정

현재 Phase 9 판정:

```text
OFFLINE CLEAN-ROOM RECONSTRUCTION: PASS
LIVE CLEAN-ROOM REPRODUCTION: BLOCKED
FINAL REPRODUCIBILITY SIGN-OFF: NOT YET
```

차단사유가 해소될 때까지 현재 rehearsal 결과를 공인시험 재현 완료로 표현하지 않는다.


## 14. Post-rehearsal qualification update

본 rehearsal 기록 당시에는 repository `.env`의 OpenAI credential이 실제 AJQG에서 401이어서 live Judge qualification을 차단요인으로 기록했다. 이후 같은 날 evaluator account-readiness revision을 commit `1d720d1`로 고정한 뒤, 서버에 이미 provision된 유효 provider credential을 **qualification subprocess에만 runtime-only로 주입**하여 fresh AJQG를 재실행했다.

결과:

- evaluator source aggregate: `0069d7c24a53339b7d586e435547544e8bf8d4a7c52395f730efbffefd76a701`
- controls: `104` × `2` repeats
- repeated decisions: `376/376` identical
- all gate metrics: `1.0000`
- AJQG: **PASS**
- submission evidence: `data/submission/evidence/ajqg_20261011/`

따라서 **Judge qualification credential 문제는 이후 해소되었다.** Phase 9 live SUT reproduction이 계속 `BLOCKED`인 원인은 dedicated empty-instruction SEEXR 시험계정과 final dated-snapshot SUT deployment가 아직 확정되지 않았기 때문이다. 본 문서 앞부분의 401 서술은 rehearsal 당시의 관찰 이력으로 유지한다.


### AJQG submission-copy normalization

Fresh AJQG의 raw `control_results.csv`는 CRLF 원본(`f362861e34544dce100d600218ce23f0953e4cb87aa915f980a830e53d3fbf58`)을 그대로 `runs/`에 보존한다. Git 제출 사본은 line ending만 LF로 정규화하여 SHA-256 `d58600def63198640101bb740ed3406efe53f06c7203d7a69d41e048b070caf6`이 되었고, 이를 source/runtime/artifact와 묶는 binding SHA-256은 `abac8aeefc86112e02e230247c42b3292c780d859c29c6d12b61a09db12354cb`이다.
