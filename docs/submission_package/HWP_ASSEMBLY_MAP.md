# HWP/HWPX Assembly Map

- Working ID: `HWP-ASSEMBLY-MAP-20261011`
- 상태: `READY_FOR_FINAL_INPUTS`
- 기준일: `2026-10-11`
- 목적: 최종 HWP/HWPX 작성 에이전트가 기술 내용을 재해석하지 않고 기존 Markdown을 붙임 구조로 조립하게 한다.

## 1. 공문 본문

권장 제목:

```text
SEEXR 위험성평가 AI KOLAS 시험 재현성 및 측정시스템 제출자료
```

본문은 1~2페이지 이내를 원칙으로 한다.

1. 제출 목적
2. 시험대상/시험방법 요약
3. 제출 붙임 목록
4. 재현시험 credential 별도 전달 안내
5. 문의 담당자

공문 본문/제출자료 개요 직후에는 `17_KOLAS_REQUEST_CROSSWALK.md`의 표를 **“시험기관 요청사항 대응표”**로 배치한다.

다음 행정값은 최종 입력 전 추정하지 않는다.

```text
{{DOCUMENT_NUMBER}}
{{DOCUMENT_DATE}}
{{RECIPIENT_ORGANIZATION}}
{{RECIPIENT_NAME_OR_TITLE}}
{{SENDER_ORGANIZATION}}
{{AUTHOR}}
{{REVIEWER}}
{{APPROVER}}
```

## 2. 붙임 1 — 시험방법 및 시험대상 시스템 명세서

Source order:

1. `01_TEST_METHOD.md`
2. `02_SYSTEM_UNDER_TEST.md`
3. `16_EXECUTION_ENVIRONMENT_REPEAT_POLICY.md`의 실행환경 부분
4. `LAB_METHOD_DECISION_REGISTER.md` — **승인 결과만 반영하고 proposal 자체는 최종 붙임에서 제거 또는 승인표로 전환**
5. `SUT_FREEZE_CANDIDATE.md` — final freeze 후 candidate 표현을 final identity 표로 전환

필수 표:

- 시험범위
- primary/secondary metric
- MATCH rule
- denominator/failure handling
- dataset 425/843
- SUT component/repository version
- stateful DB content identity

## 3. 붙임 2 — 모델·추론 고정 설정 명세서

Source:

- `03_INFERENCE_CONFIGURATION.md`
- `12_VERSION_MANIFEST.md`의 model/runtime 부분

필수 표:

- agent/stage/model snapshot
- KOLAS model env
- temperature/top_p/seed/max token/provider-controlled 여부
- execution profile/model mode/reasoning style
- dependency/runtime

## 4. 붙임 3 — Ground Truth 구성·출처·검증 상태 보고서

Source:

1. `04_GT_SPECIFICATION.md`
2. `05_GT_SOURCE_PROVENANCE.md`
3. `15_TEST_DATA_INDEPENDENCE_AUDIT.md`
4. `data/cases/dataset_manifest.json`
5. `data/cases/gt_provenance_audit_manifest_v1.json`

표현 원칙:

- `KOLAS_RA_GT v1.0.0`
- 425 scenarios / 843 reference hazards
- canonical hash 명시
- 연구실 구성원 검토·검증 완료 사실만 기재
- 확인되지 않은 검증 인원수, κ, 합의율을 창작하지 않음
- GT 검증상태와 original-source provenance coverage를 구분

## 5. 붙임 4 — 측정시스템(Evaluator/Judge) 명세 및 적격성 검증

Source:

1. `08_EVALUATOR_SPECIFICATION.md`
2. `09_EVALUATOR_QUALIFICATION.md`
3. `data/submission/evidence/ajqg_20261011/binding.json`
4. AJQG summary/table

필수 값:

- Judge `gpt-5.6-sol`
- reasoning `medium`
- prompt/rubric hash
- source aggregate
- 104 controls ×2
- 376/376 stability
- all gate metrics 1.0000
- gate PASS

AJQG control raw response를 본문에 장황하게 넣지 않고 summary + checksum + 필요 시 별도 전자자료로 제공한다.

## 6. 붙임 5 — 재현 절차 및 API 접속 가이드

Source:

1. `10_REPRODUCIBILITY_GUIDE.md`
2. `11_API_ACCESS_GUIDE.md`
3. `16_EXECUTION_ENVIRONMENT_REPEAT_POLICY.md`의 반복/세션/캐시 부분
4. `CLEAN_ROOM_REHEARSAL_20261011.md`의 최종 결과 부분

필수 구조:

- prerequisites
- code/GT/credential 3-part 전달구조
- `uv sync --frozen`
- integrity verify
- `doctor --live --official --require-ready`
- AJQG
- official run
- seal/verify
- credential revoke

실제 secret은 `[별도 보안채널 제공]`으로만 표기한다.

## 7. 붙임 6 — 버전·무결성·변경통제 명세서

Source:

1. `12_VERSION_MANIFEST.md`
2. `13_INTEGRITY_MANIFEST.md`
3. `14_CHANGE_CONTROL.md`
4. `15_TEST_DATA_INDEPENDENCE_AUDIT.md`의 시험조건 결정/overlap evidence

최종본에서는 다음을 반드시 full-length로 기록한다.

- final Git tag/commit
- Core/Agents/RA/Law commit/tree
- source fingerprint
- RA/Law content root
- final submission artifact root
- HWP/HWPX/PDF 개별 SHA-256

## 8. 붙임 7 — 제출 전자자료 목록

권장 분류:

1. HWP/HWPX
2. PDF preview
3. checksum manifest
4. evaluator source 또는 release archive
5. secure GT package
6. AJQG evidence
7. run artifact/seal
8. API access/readme
9. 필요 시 secure DB backup artifact

각 행:

```text
번호 | 파일명 | 버전 | SHA-256 | 보안등급/전달경로 | 비고
```

## 9. 그림/표 numbering contract

각 붙임은 자체 표 번호를 사용하거나 통합 기술보고서 요구 시 전체 연속번호를 사용한다. 혼용하지 않는다.

권장 그림:

- 그림 1. 시험 측정 흐름
- 그림 2. SUT 구성 및 외부 dependency 경계
- 그림 3. 재현 패키지/무결성 chain

권장 핵심 표:

- 표 1. 시험범위 및 지표
- 표 2. SUT version
- 표 3. 모델/추론 설정
- 표 4. GT identity
- 표 5. Judge freeze
- 표 6. AJQG qualification
- 표 7. API 최소권한
- 표 8. 재현 실행환경
- 표 9. checksum/version
- 표 10. 변경통제

## 10. 최종 조립 전 자동 차단

다음이면 최종 `APPROVED/FROZEN` HWP를 만들지 않는다.

- `LAB_METHOD_DECISION_REGISTER.md`가 PROPOSAL 상태
- `DEC-METHOD-010`(GT↔RA overlap 시험조건/해석) 미승인
- SUT freeze가 PRE_FREEZE
- dedicated account readiness 미완료
- clean-room live full run 미완료
- final submission root 미생성
- 행정 placeholder 미입력
- secret 평문 발견

## 11. 현재 상태

현재 구조/소스 매핑은 완료되어 있다. **최종 조립 자체만 외부/사람 입력을 기다린다.**
