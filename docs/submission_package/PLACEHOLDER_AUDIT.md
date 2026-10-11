# HWP 최종화 Placeholder Audit

- Working ID: `PLACEHOLDER-AUDIT-20261011`
- 상태: `COMPLETE_FOR_CURRENT_CANDIDATE`
- 기준일: `2026-10-11`
- 검사범위: `docs/submission_package/*.md`
- 결과: **22 unique placeholders / 36 occurrences**

> placeholder가 남아 있다는 사실 자체가 오류는 아니다. 현재 candidate에서는 final deployment 또는 행정정보가 아직 확정되지 않았기 때문에 의도적으로 남겨둔 값이 있다. 최종 `APPROVED/FROZEN` 문서에서는 아래 “blocking” placeholder가 0건이어야 한다.

## 1. Final deployment / test identity — blocking 9종

| Placeholder | 의미 | Owner / 해소시점 |
|---|---|---|
| `{{CORE_FINAL_COMMIT}}` | Core final commit/tag identity | final SUT freeze |
| `{{AGENTS_FINAL_COMMIT}}` | Agents final commit/tag identity | final SUT freeze |
| `{{RA_FINAL_COMMIT}}` | RA final commit/tag identity | final SUT freeze |
| `{{LAW_FINAL_COMMIT}}` | Law final commit/tag identity | final SUT freeze |
| `{{FINAL_MEASUREMENT_RELEASE_TAG}}` | evaluator/submission final release | final freeze/sign-off |
| `{{FINAL_SUT_BASE_URL}}` | accredited test endpoint | SUT deployment 승인 |
| `{{FINAL_DEPLOYMENT_IMAGE_OR_OS_ID}}` | immutable deployment runtime identity | deployment freeze |
| `{{EVAL_ACCOUNT_ID_HASH}}` | dedicated evaluation account pseudonymous identity | account provisioning |
| `{{KOLAS_TEST_ACCOUNT_ID}}` | institution/test account identifier | account provisioning |

현재 candidate commit/tree/fingerprint는 이미 `SUT_FREEZE_CANDIDATE.md`에 존재한다. 위 placeholder에는 **final 승인 후 실제 배포값**만 넣는다.

## 2. HWP administrative metadata — blocking 11종

| Placeholder | 의미 |
|---|---|
| `{{AUTHOR}}` | 작성자 |
| `{{REVIEWER}}` | 검토자 |
| `{{APPROVER}}` | 승인자 |
| `{{DOCUMENT_DATE}}` | 공문 발행일 |
| `{{DOCUMENT_NUMBER}}` | 조립 map의 문서번호 |
| `{{ISSUE_DATE}}` | HWP handoff 기준 발행일 |
| `{{OFFICIAL_DOCUMENT_NUMBER}}` | 공식 문서번호 |
| `{{RECIPIENT_ORGANIZATION}}` | 수신기관 |
| `{{RECIPIENT_NAME_OR_TITLE}}` | 수신자/직위 |
| `{{REFERENCE_RECIPIENT}}` | 참조처/참조인 |
| `{{SENDER_ORGANIZATION}}` | 발신기관 |

기관 양식이 위 필드 중 일부를 사용하지 않으면 최종 template에서 해당 필드를 제거하고 “빈 문자열로 추정”하지 않는다.

## 3. 설명/템플릿용 — non-blocking 2종

| Placeholder | 위치/용도 | 최종 처리 |
|---|---|---|
| `{{PLACEHOLDER_NAME}}` | README의 placeholder 문법 예시 | 설명문이므로 유지 가능 |
| `{{PLACEHOLDER}}` | HWP_HANDOFF/MASTER_PLAN/README의 일반 규칙 예시 | 설명문이므로 유지 가능 |

이 두 표현은 실제 미입력 필드가 아니라 **placeholder 규칙을 설명하기 위한 literal example**이다.

## 4. Cross-reference source existence audit

`HWP_ASSEMBLY_MAP.md`가 참조하는 주요 source를 모두 filesystem에서 확인했다.

### 붙임 source — 15/15 PASS

- `01_TEST_METHOD.md`
- `02_SYSTEM_UNDER_TEST.md`
- `LAB_METHOD_DECISION_REGISTER.md`
- `SUT_FREEZE_CANDIDATE.md`
- `03_INFERENCE_CONFIGURATION.md`
- `12_VERSION_MANIFEST.md`
- `04_GT_SPECIFICATION.md`
- `05_GT_SOURCE_PROVENANCE.md`
- `08_EVALUATOR_SPECIFICATION.md`
- `09_EVALUATOR_QUALIFICATION.md`
- `10_REPRODUCIBILITY_GUIDE.md`
- `11_API_ACCESS_GUIDE.md`
- `CLEAN_ROOM_REHEARSAL_20261011.md`
- `13_INTEGRITY_MANIFEST.md`
- `14_CHANGE_CONTROL.md`

### Evidence source — 3/3 PASS

- `data/cases/dataset_manifest.json`
- `data/cases/gt_provenance_audit_manifest_v1.json`
- `data/submission/evidence/ajqg_20261011/binding.json`

## 5. Final HWP gate

최종 조립 직전에 다음 검사를 다시 한다.

```text
blocking placeholders = 0
missing assembly sources = 0
secret matches = 0
integrity mismatches = 0
```

현재는 blocking placeholders가 의도적으로 남아 있으므로 HWP/HWPX 상태를 `APPROVED/FROZEN`으로 올리지 않는다.
