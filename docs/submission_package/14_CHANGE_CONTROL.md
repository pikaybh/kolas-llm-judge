# KOLAS 제출자료 변경통제 및 재시험 판정 규칙

- 문서 ID: `KOLAS-DOC-014`
- 버전: `0.1-review`
- 상태: `REVIEW`
- 기준일: `2026-10-11`
- 적용대상: GT, SUT, Evaluator/Judge, 시험방법, 실행환경, API/Auth, 제출 전자자료

> Freeze 이후의 변경은 “파일을 다시 저장한 것”과 “시험 결과의 의미를 바꿀 수 있는 변경”을 구분한다. 모든 변경은 before/after identity, 변경사유, 영향분석, 필요한 재검증/재시험을 기록하며 기존 evidence를 덮어쓰지 않는다.

## 1. 상태 모델

| 상태 | 의미 | 허용행위 |
|---|---|---|
| `PRE-FREEZE` | 제출 후보를 준비 중 | 통상 변경 가능, 변경이력 유지 |
| `FROZEN-CANDIDATE` | 시험용 version/hash가 고정된 후보 | 승인된 변경만 가능, manifest 재생성 필수 |
| `TEST-IN-PROGRESS` | 공식 시험이 시작됨 | 원칙적으로 변경 금지 |
| `SEALED` | 시험 종료 후 run seal 검증 완료 | 결과·artifact 수정 금지, 정정은 새 release/run으로 수행 |
| `SUPERSEDED` | 새 승인버전으로 대체됨 | 보존만 하고 신규 공식시험에는 사용하지 않음 |

`TEST-IN-PROGRESS` 중 SUT/evaluator/GT/runtime identity가 변경되면 해당 run의 공식 유효성을 재평가한다. 결과에 영향을 줄 수 있는 변경은 기존 run을 그대로 공식 결과로 승계하지 않는다.

## 2. 변경기록 필수항목

각 변경은 최소 다음 정보를 가진다.

- Change ID
- 요청일 / 적용일
- 요청자
- 검토자 / 승인자
- 변경분류
- 변경사유
- 대상 artifact/component
- before version/commit/SHA-256
- after version/commit/SHA-256
- 시험방법/성능결과 영향
- 보안/운영 영향
- 필요한 재검증/재시험 범위
- 수행한 test/run ID와 결과
- 새 integrity manifest/root digest
- 기존 release/run의 상태 (`valid`, `superseded`, `invalidated` 등)

실제 secret은 변경기록에 남기지 않는다.

## 3. 변경분류 및 기본 재시험 규칙

### Class A — 문서 편집만 변경

예:

- 오탈자
- 표/문단 배치
- 의미를 바꾸지 않는 공문 서식
- 링크 표기 정정

조건:

- 기술값, 계산식, 판정규칙, 버전/hash, API contract의 의미가 바뀌지 않음

조치:

- 변경검토
- integrity manifest 재생성
- HWP/PDF checksum 재생성
- SUT 성능시험 재실행 불필요

### Class B — provenance / 행정 metadata 변경

예:

- source locator 보강
- license/access 상태 확인
- 담당자/문서번호 기입
- GT 내용은 그대로인 provenance metadata 보강

조치:

- GT content/hash 불변 확인
- provenance/register/manifest 갱신
- impact review
- 성능평가 재실행은 원칙적으로 불필요

단, provenance 보강 과정에서 GT 내용 자체를 수정하면 Class C로 승격한다.

### Class C — GT content / scenario 구성 변경

예:

- hazard 문구 수정
- reference 추가/삭제/merge/split
- scenario grouping 변경
- 시험입력 context 변경

조치:

- `KOLAS_RA_GT` 새 content version 부여
- old→new reference mapping 작성
- dataset/scenario hash 재고정
- evaluator input identity 갱신
- **전체 official 성능시험 재실행**

기존 `v1.0.0` evidence는 삭제하지 않는다.

### Class D — Evaluator/Judge/시험방법 변경

예:

- Judge model/reasoning 변경
- prompt/rubric 변경
- structured output schema 변경
- AJQG seed/control/gate 변경
- semantic match rule 변경
- denominator 변경
- aggregation/matching algorithm 변경
- 성능 합격판정 기준 변경

조치:

- evaluator version 변경
- source/config hash 재고정
- AJQG 재qualification
- 계산 의미에 영향을 주면 기존 SUT 결과의 재계산만으로 충분한지 검토
- SUT-generated raw output에 없는 정보가 필요하거나 판정 semantics가 변경되면 **전체 official 시험 재실행**
- 시험기관과 이미 합의된 시험방법 변경은 사전 승인/통지 필요

### Class E — SUT 변경

예:

- Core/Agents code 변경
- model identifier/snapshot 변경
- prompt/workflow/tool 변경
- retrieval/ranking algorithm 변경
- RA DB/embedding snapshot 변경
- Law DB snapshot 변경
- saved instruction 또는 시험 context 변경
- dependency/runtime 변경으로 inference 동작 가능성이 달라짐

조치:

- 새 SUT release/commit identity 부여
- 관련 stateful snapshot 재고정
- preflight 재수행
- **전체 official 성능시험 재실행**

### Class F — API/Auth/Infrastructure 변경

예:

- base URL/TLS/reverse proxy 변경
- auth token TTL/refresh policy 변경
- rate limit 변경
- 시험계정 role/entitlement 변경
- 컨테이너/OS/네트워크 설정 변경

조치:

- API/auth preflight 재실행
- clean-room drill 재수행 여부 검토
- 결과 내용 또는 실행경로에 영향을 줄 가능성이 있으면 전체 official 시험 재실행
- 시험 도중 변경이 발생하면 run validity 우선 재평가

### Class G — Evaluator dependency 변경

예:

- OpenAI SDK
- Pydantic
- Python runtime
- deterministic parser/serialization dependency

조치:

- lockfile/version identity 갱신
- evaluator regression test
- AJQG 재실행
- structured parsing 또는 판정 semantics 영향이 있으면 full retest 여부 검토

SUT dependency 변경은 Class E로 취급한다.

## 4. 긴급 보안수정

보안 취약점 대응이라도 freeze를 몰래 우회하지 않는다.

1. 변경 전 artifact identity 보존
2. 보안위험과 시험영향을 각각 기록
3. 변경 적용
4. 새 commit/release와 manifest 생성
5. 해당 변경분류의 최소 재검증 수행
6. 결과 영향을 배제할 수 없으면 전체 재시험
7. 기존 candidate를 `SUPERSEDED` 또는 `INVALIDATED`로 명시

“보안수정이므로 시험에는 영향이 없다”는 근거 없는 간주를 하지 않는다.

## 5. 시험 중 변경탐지

Official runner는 시험 시작 시 Core/Agents relevant source fingerprint를 기록하고 종료 후 다시 계산한다.

다음 중 하나가 발생하면 즉시 조사한다.

- start/end SUT source fingerprint 불일치
- evaluator source hash 불일치
- GT/scenario hash 불일치
- official runtime/prompt/rubric hash 불일치
- unexpected artifact 수정
- run seal verification 실패

공식 candidate validity rule이 false이면 보고서의 성능값이 존재하더라도 공인 결과로 승계하지 않는다.

## 6. Integrity manifest 갱신 규칙

`data/submission/submission_integrity_manifest_v1.json`은 제출후보 파일의 path, size, SHA-256과 artifact root digest를 기록한다.

다음 경우 반드시 다시 생성한다.

- manifest 대상 파일 내용 변경
- 파일 추가/제거
- freeze candidate version 변경
- 제출 전 최종 HWP/PDF/전자자료 구성 확정

재생성 시 이전 manifest는 audit evidence로 보존한다. 최종 release에서는 manifest SHA-256과 artifact root SHA-256을 공문/전자자료 목록 또는 별도 checksum 기록에 기재한다.

## 7. Version 정책

| 대상 | 현재 version/identity 정책 |
|---|---|
| GT content | `KOLAS_RA_GT v1.0.0`; 내용 변경 시 새 dataset version |
| GT provenance | content 불변이면 별도 provenance revision으로 보강 가능 |
| Judge pipeline | `binary-checklist-v1`; 판정 semantics 변경 시 version 증가 |
| AJQG | seed/gate/control suite 각각 version/hash로 식별 |
| official runtime | `official-runtime-v1`; frozen 시험계약 변경 시 새 version |
| SUT | Core/Agents/RA/Law commit + stateful snapshot + deployment identity |
| submission package | Git commit/tag + integrity manifest root |
| official run | unique run ID + `run_seal.json` root |

## 8. 승인 책임

최종 조직명/직책은 HWP 행정정보 확정 시 채운다. 기술적으로 최소 다음 역할을 분리한다.

- 변경 요청자
- 기술 검토자
- 최종 승인자
- 시험 운영자

동일인이 여러 역할을 수행해야 할 경우 그 사실을 기록한다. 확인되지 않은 승인자 이름을 임의 작성하지 않는다.

## 9. 변경 후 검증 매트릭스

| 변경 | 문서/hash 재생성 | Regression | AJQG | API preflight | Full SUT retest |
|---|---:|---:|---:|---:|---:|
| A 문서 편집 | 필수 | 필요 시 | 불필요 | 불필요 | 불필요 |
| B provenance/admin | 필수 | 필요 시 | 불필요 | 불필요 | 원칙상 불필요 |
| C GT content | 필수 | 필수 | 필요 시 | 필요 시 | **필수** |
| D evaluator/method | 필수 | **필수** | **필수** | 필요 시 | 영향에 따라 필수 |
| E SUT | 필수 | **필수** | 시험 전 필수 | **필수** | **필수** |
| F API/infra | 필수 | 필요 시 | 시험 전 필수 | **필수** | 영향에 따라 필수 |
| G evaluator dependency | 필수 | **필수** | **필수** | 필요 시 | 영향에 따라 필수 |

## 10. 최종 freeze 전 체크

- [ ] 최종 evaluator commit/tag 확정
- [ ] 최종 SUT Core/Agents/RA/Law commit 확정
- [ ] RA/Law stateful snapshot hash 확정
- [ ] final SUT base URL 확정
- [ ] 시험계정 identity/empty Saved Instruction/entitlement 확인
- [ ] 유효 OpenAI credential로 AJQG PASS
- [ ] clean-room drill PASS
- [ ] 모든 제출 문서 `APPROVED` 또는 명시적 `REVIEW` 상태 정리
- [ ] `submission_integrity_manifest_v1.json` 최종 재생성
- [ ] HWP/HWPX/PDF 생성 후 각각 checksum 기록
- [ ] 최종 tag/release 생성

현재 2026-10-11 상태는 최종 `FROZEN`이 아니라 **submission candidate preparation** 단계다.
