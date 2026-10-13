# KOLAS 최종화 Blocker Register

- Working ID: `FINALIZATION-BLOCKERS-20261011`
- 상태: `ACTIVE`
- 기준일: `2026-10-11`
- 목적: 최종 HWP/HWPX·공인시험·release를 막는 항목을 **사람 결정 / 외부기관 결정 / 자동실행**으로 분리한다.

> 이 문서에 없는 기술값을 최종화 에이전트가 추정해서 채우지 않는다. blocker가 해소되면 evidence를 남기고 해당 행을 `RESOLVED`로 바꾼다.

## 1. 현재 결론

현재 package는 **기술 준비도는 높지만 최종 공인시험 실행 가능 상태는 아니다.**

이미 완료된 핵심 기술 준비:

- GT identity / lineage / provenance audit
- evaluator source/runtime freeze candidate
- current-source AJQG PASS
- SUT model dated-snapshot pinning 경로 및 provider smoke PASS
- evaluation-account Saved Instruction / allowance automatic gate
- clean-room offline reconstruction
- Core/Agents source fingerprint
- RA/Law deterministic DB content fingerprint
- submission integrity / change control
- 시험기관 method decision proposal

남은 핵심은 **승인·계정·최종 배포 freeze·실제 live full run·행정정보**다.

2026-10-13 추가 감사에서 GT와 runtime RA retrieval DB 사이에 substantial exact-content overlap이 확인되었다. 따라서 공식시험 전에 `BLK-LAB-010`을 반드시 해소해야 한다.

## 2. Human / SEEXR owner blockers

| ID | 항목 | 필요한 입력/행동 | 현재 상태 | 이후 자동화 |
|---|---|---|---|---|
| `BLK-HUM-001` | Dedicated 시험계정 | 시험기관 또는 시험용 email/account 확정; active `Role.USER`, Saved Instruction empty, 충분한 AI allowance | BLOCKED | account preflight → hash 기록 → clean-room live auth |
| `BLK-HUM-002` | Final SUT deployment 선택 | 공인시험에 사용할 immutable deployment/base URL 결정 | BLOCKED | Core/Agents/RA/Law fingerprint 재수집 → model env 검증 → doctor |
| `BLK-HUM-003` | Final release/tag 승인 | candidate commits를 final release로 승인 | BLOCKED | tags/release 작성 → version manifest 갱신 |
| `BLK-HUM-004` | HWP 행정정보 | 문서번호, 수신기관/수신자, 발신기관, 작성/검토/승인자 | BLOCKED | 공문 본문 자동 조립 |
| `BLK-HUM-005` | 기관 양식 | 기관 공식 HWP/HWPX 양식 또는 작성요령이 있으면 제공 | BLOCKED/OPTIONAL | 해당 template에 최종 문서 조립 |

### 현재 시험계정을 그대로 쓰면 안 되는 이유

현재 내부 rehearsal 계정은 authenticated API와 AI allowance는 정상이나 Saved Instruction이 **NON_EMPTY**다. instruction 원문은 기록하지 않았으며 official preflight가 이를 자동 FAIL 처리한다. 해당 계정을 임의로 수정하지 않는다.

## 3. Testing laboratory / external approval blockers

| ID | Decision | SEEXR proposal | 현재 상태 |
|---|---|---|---|
| `BLK-LAB-001` | Primary metric | Hazard Semantic Identification Recall | APPROVAL REQUIRED |
| `BLK-LAB-002` | MATCH rule | mechanism AND context | APPROVAL REQUIRED |
| `BLK-LAB-003` | Denominator | **all selected references; SUT non-completion = missed** | APPROVAL REQUIRED |
| `BLK-LAB-004` | Dataset | 425 scenarios / 843 refs | APPROVAL REQUIRED |
| `BLK-LAB-005` | Full-run repeats | 2회 | APPROVAL REQUIRED |
| `BLK-LAB-006` | Repeat tolerance | report-only 우선; Pass/Fail 필요 시 별도 사전합의 | APPROVAL REQUIRED |
| `BLK-LAB-007` | Judge gate | frozen AJQG mandatory | APPROVAL REQUIRED |
| `BLK-LAB-008` | Product performance threshold | 외부 규격 없으면 measured-value report | APPROVAL REQUIRED |
| `BLK-LAB-009` | Local DB restore 필요 여부 | frozen remote SUT 사용 시 불필요; local restore 요구 시 secure backup 제공 | CONFIRMATION REQUIRED |
| `BLK-LAB-010` | GT ↔ RA retrieval DB 중복의 시험 해석 | 통합제품 end-to-end로 시험하며 overlap 명시, 또는 독립 holdout/leakage-controlled 조건을 기관과 별도 확정 | **APPROVAL REQUIRED / CRITICAL** |

상세 선택표: `LAB_METHOD_DECISION_REGISTER.md`.

## 4. 사용자 개입 없이 자동으로 수행할 후속 작업

아래 항목은 위 blocker가 풀리면 별도 설계논의 없이 바로 실행한다.

1. final deployment의 Core/Agents/RA/Law commit/tree/fingerprint 재수집
2. dated model env effective value 확인
3. RA/Law content fingerprint 재캡처 및 candidate 비교
4. dedicated account Saved Instruction empty SHA 확인
5. `doctor --live --official --require-ready`
6. frozen AJQG 재실행
7. clean-room sample run
8. full 425-case run × 승인된 반복횟수
9. seal / verify / source end-fingerprint 확인
10. repeatability 분석
11. 최종 성능표 생성
12. Markdown status `APPROVED/FROZEN` 정리
13. HWP/HWPX + PDF 생성
14. 최종 delivery checksum manifest 생성
15. Git tag/release
16. 기관 전달 후 credential revoke 기록

## 5. 현재 기술적으로 남은 비인간 작업

### 5.1 Final deployment 직전 실행할 것

현재 candidate에 대해 미리 실행하면 최종 freeze 때 다시 해야 하므로 지금 수행하지 않는다.

- final source fingerprint
- final DB fingerprint
- final deployment model env check
- final account readiness
- final live AJQG
- final sample/full run

### 5.2 DB backup artifact

현재는 RA/Law content SHA-256 fingerprint가 존재한다. `pg_dump` client가 현재 host에 설치되어 있지 않고, disk가 약 98% 사용 중이다. **기관이 local DB restore를 요구하지 않는 한 대형 backup artifact를 선제 생성하지 않는다.**

기관이 요구하면 운영자가 secure snapshot/export를 만들고 다음만 제출 package에 기록한다.

- artifact name/version
- encrypted or secure delivery location
- SHA-256
- restore procedure
- PostgreSQL/version/extension prerequisites

DB credential이나 raw dump를 Git에 넣지 않는다.

## 6. Stop / Go 기준

### 지금 GO 가능한 것

- 문서 품질검사
- cross-reference 검사
- HWP 조립 source 정리
- 기관 협의안 송부 준비

### 지금 GO 하면 안 되는 것

- 현재 내부 계정으로 공식 425-case run
- 개발 Green endpoint를 최종 공인 endpoint라고 임의 확정
- method decision 미승인 상태에서 denominator code 변경
- final Git tag 생성
- `APPROVED/FROZEN` HWP 발행

## 7. 사용자에게 실제로 요청할 시점

다음 중 하나가 먼저 발생할 때 사용자에게 요청한다.

1. 시험기관 method decision 회신을 받아야 더 진행할 수 있을 때
2. dedicated 시험계정 email/credential provisioning이 필요할 때
3. final SUT deployment/base URL을 인간이 승인해야 할 때
4. HWP 수신/발신/결재 정보를 채워야 할 때
5. 기관 공식 HWP template가 반드시 필요한 것으로 확인될 때

그 전까지는 기술문서·검증·자동화 작업을 계속 수행한다.
