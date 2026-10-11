# KOLAS 재현성 패키지 마스터 계획

- 문서 ID: `KOLAS-PLAN-001`
- 상태: `IN_PROGRESS`
- 목적: 작업이 중단되어도 다른 에이전트가 동일한 기준으로 즉시 재개할 수 있는 작업 원장
- 최종 산출물: 공문형 HWP/HWPX + 별첨 재현 패키지
- GitHub 작업 원장: `pikaybh/kolas-llm-judge#1`

## 현재 재개 지점

> **Phase 0 — 기존 구현과 증적을 제출 기준으로 재감사하는 단계부터 시작한다.**
> 이 repository에는 이미 `configs/official_runtime_v1.yaml`, `KOLAS_RA_GT v1.0.0`, frozen Rubric/prompt, evaluator 코드, official-live/반복성/seal 관련 산출물이 존재한다. 새로 만드는 것이 아니라 **현재 구현을 evidence ID와 제출문서 항목에 연결하고, GT provenance 등 제출에 필요한 추적정보를 정리**한다. GT 자체는 연구실 구성원들의 검토를 거쳐 이미 검증된 데이터로 취급한다.

## Phase 0. 기존 자료 및 구현 재감사 / Evidence Inventory

- [x] 현재 repository의 KOLAS 코드·스크립트·GT·sealed run·derived 결과·문서 위치를 evidence inventory로 등록
- [x] `KOLAS_RA_GT v1.0.0`의 425 scenarios / 843 reference hazards canonical 원본·manifest·hash 재확인
- [x] 과거 실행 결과(예: broad/strict semantic 평가)가 생성된 실제 스크립트와 raw 결과 확인
- [x] 현재 SUT 호출 경로(`seexr-api-core` → agents/RA 등) 실제 코드 기준 정리
- [x] 현재 사용 모델을 agent별로 코드/환경설정/API 요청 기준 확인
- [x] 모델 provider가 실제로 허용하는 추론 파라미터 목록 확인
- [x] temperature/top_p/seed/reasoning effort 등 각 파라미터의 `고정/미사용/미지원/provider-controlled` 상태 확인
- [x] system/user prompt 및 structured-output schema의 실제 소스 위치 확인
- [x] retry/timeout/concurrency/rate-limit 정책 확인
- [x] 기존 evaluator/Judge 구현, `judge_binary_v1.md`, `rubric_binary_v1.yaml`, official runtime freeze의 정합성 재확인
- [x] Git에 포함되지 않은 sealed run/raw artifact/전문가 자료 등 외부 증적과 보관 위치 조사
- [x] 민감정보/개인정보가 제출 패키지에 섞일 가능성 점검
- [x] 감사 결과를 `evidence inventory`로 작성

**완료 조건:** 모든 이후 문서에서 참조할 수 있는 파일 경로/commit SHA/evidence ID 목록이 존재한다.

**Phase 0 Evidence:** `00_PHASE0_EVIDENCE_INVENTORY.md`, `00_PHASE0_AUDIT_LOG.md`
**결론:** 완료. 발견된 미충족 사항은 `GAP-*`로 후속 Phase에 이관.


## Phase 1. 시험 범위와 측정방법 Freeze

- [x] 시험 목적과 대상 기능을 한 문장으로 확정
- [x] 공식 측정 지표명 확정
- [ ] denominator/numerator 최종 확정 — numerator는 정의 완료, denominator는 `DEC-METHOD-003` 시험기관 승인 대기
- [x] scenario 단위와 reference hazard 단위 관계 정의
- [x] semantic MATCH 조건 확정
- [x] generated hazard atomic decomposition 규칙 확정
- [x] 다수 generated hazard가 하나의 GT에 대응할 때 규칙 정의
- [x] 하나의 generated hazard가 여러 GT에 대응할 때 규칙 정의
- [x] SUT 실패/timeout/invalid schema 처리 규칙 정의
- [x] 재시도 횟수와 실패가 metric에 반영되는 방식 정의
- [ ] 동일 입력 반복 시험 횟수 및 허용 변동 최종 확정 — 통계 항목/최소 2회 후보 정의, `DEC-METHOD-005/006` 승인 대기
- [x] 시험기관과 합의가 필요한 항목을 별도 표로 분리
- [ ] `01_TEST_METHOD.md` 승인본 작성 — 현재 `0.2-draft / REVIEW`, 외부 method decision 이후 승인

**완료 조건:** 동일 raw data를 주면 별도 해석 없이 같은 metric을 계산할 수 있다.

**Phase 1 Draft:** `01_TEST_METHOD.md`
**현재 상태:** 내부 구현 설명은 정리 완료. denominator·반복/허용변동·성능 합격선은 시험기관 승인 전 freeze 금지.

## Phase 2. SUT 및 추론 설정 Freeze

- [x] 시험대상 freeze candidate ID 부여 — `SEEXR-RA-SUT-RC-2026.10.11.1`; final release tag는 freeze gate 이후 부여
- [x] 관련 repository별 commit SHA 기록 — Core/Agents/RA/Law audit snapshot 및 Git tree 기록
- [x] API endpoint와 request/response schema version 기록 — protocol v2 / quick-fast-v1.0.0 / SSE/XML contract 기록
- [x] agent별 모델 identifier 기록 — normal/conditional KOLAS path 분리 기록
- [x] reasoning/fast/instant 등 provider mode를 실제 요청 기준 기록 — SEEXR `fast`와 OpenAI service tier를 분리하고 SUT service tier 직접 설정 없음 확인
- [x] temperature/top_p/max tokens/seed 등 설정값 기록 — relevant quick-fast source에서 explicit 설정 없음 확인
- [x] 설정 불가 값은 `미지원` 또는 `provider-controlled`로 명시
- [x] prompt 파일 또는 prompt content hash 기록 — 단일 prompt 파일 대신 agent/workflow/prompt-builder source SHA-256 집합으로 기록
- [x] tool/function/schema 설정 기록 — RA hybrid retrieval, structured-output schemas, conditional branches 정리
- [x] dependency/runtime 버전 기록 — Node/npm/package-lock 및 주요 resolved package 기록
- [ ] DB/schema/migration 최종 상태 기록 — RA API-visible 6,443행 hash 확보; embedding 포함 RA snapshot 및 Law DB snapshot은 PENDING
- [x] feature flag 및 환경변수 중 시험에 영향을 주는 값 목록화 — secret 제외 whitelist와 source default/override 경로 기록
- [x] `02_SYSTEM_UNDER_TEST.md`, `03_INFERENCE_CONFIGURATION.md`, `12_VERSION_MANIFEST.md` REVIEW 초안 작성

**완료 조건:** 시험기관이 어떤 버전/모델/설정으로 호출해야 하는지 모호성이 없다.

**Phase 2 Drafts:** `02_SYSTEM_UNDER_TEST.md`, `03_INFERENCE_CONFIGURATION.md`, `12_VERSION_MANIFEST.md`
**현재 상태:** 소스/API/모델/prompt/runtime 감사 완료. final immutable deployment, evaluation-account instruction, RA embedding snapshot, Law DB snapshot, model snapshot policy가 남아 있어 Phase 2는 아직 `REVIEW`다.

## Phase 3. GT 정당성·출처·무결성 확립

- [x] GT canonical 파일 결정 — raw `b76c9efa...`, scenarios `2cdc1e8b...`, manifest `e7679fab...`
- [x] GT schema와 필드 정의 — 실제 11개 raw fields + scenario/reference schema 기록
- [x] scenario/reference ID를 영구 ID로 고정 — v1.0.0 내 ID 규칙·안정성 범위·migration rule 정의
- [x] duplicate/near-duplicate 점검 — 완전 중복 row 0; 전역 동일 hazard 문구 24 groups/31 extra rows, 동일 scenario 내 exact/equivalent/near 6쌍을 expert-review 대상으로 유지
- [ ] 각 reference hazard의 authoritative source provenance 연결 — legacy source-row lineage는 843/843 완료, authoritative safety source는 현재 0/843
- [x] 법령/공공기관 자료/가이드/논문/현장자료 등 source type 정의 — `kolas-gt-provenance-v1` taxonomy 작성
- [x] 원문 인용/source locator 기록 규격 정의 — 실제 843건 source locator 채움은 provenance reconstruction에서 수행
- [ ] source의 라이선스/외부 제공 가능 여부 확인 — register 필드는 정의했으나 실제 source가 미복원되어 미확정
- [x] source 미확정 항목 처리 규칙 정의 — 증거 없는 `expert-authored` 분류 금지, 현재는 `LEGACY_WORKBOOK_ONLY`
- [x] GT 변경 이력 생성 — `data/cases/GT_CHANGELOG.md`, content version과 provenance revision 분리
- [x] freeze candidate 생성 — `KOLAS_RA_GT v1.0.0`, `CONTENT-FROZEN / LAB-VALIDATED / PROVENANCE-INCOMPLETE`
- [x] GT 파일 SHA-256 계산 및 deterministic byte-for-byte rebuild 검증
- [x] `04_GT_SPECIFICATION.md`, `05_GT_SOURCE_PROVENANCE.md` REVIEW 초안 작성

**완료 조건:** 임의의 GT 항목 하나를 선택해도 근거 출처와 생성/수정 이력을 추적할 수 있다.

**Phase 3 Drafts:** `04_GT_SPECIFICATION.md`, `05_GT_SOURCE_PROVENANCE.md`, `data/cases/GT_CHANGELOG.md`, `configs/gt_provenance_schema_v1.yaml`
**현재 상태:** 파일 계보·schema·ID·hash·변환 무결성은 확인 완료. 843개 reference의 원작성 source provenance와 source license는 별도 문제로 남아 있으나, GT 자체는 연구실 구성원들의 검토를 거쳐 이미 검증된 데이터로 취급한다. 따라서 추가 GT 검증을 새로 수행하는 것은 범위에 포함하지 않는다.

## Phase 4. 기존 GT 검증 사실 기록

- [x] `KOLAS_RA_GT v1.0.0`은 연구실 구성원들이 이미 검토·검증한 데이터셋임을 명시
- [x] 본 제출 준비 과정에서 별도의 신규 전문가 검증 절차를 요구하지 않음
- [x] 기존 검증의 세부 인원수·방법·일치도 통계는 확인된 근거 없이 임의 작성하지 않음

**현재 상태:** GT는 연구실 내부 검토를 거쳐 검증된 데이터로 사용한다. 본 단계의 목적은 새로운 검증 수행이 아니라 그 사실을 제출문서에 정확히 기록하는 것이다.

## Phase 5. Evaluator / LLM Judge 측정시스템 검증

- [x] evaluator 입력/출력 schema 확정 — Match/Quality/Safety Boolean structured schema 확인
- [x] Judge model identifier와 reasoning 설정 확정 — `gpt-5.6-sol`, `medium`
- [x] Judge prompt/rubric freeze — official runtime SHA 검증
- [x] Boolean 판정 로직 및 aggregation 로직 freeze — primary rule + deterministic Python aggregation 확인
- [x] control set 정의 및 expected decision 확인 — 8 seeds → 104 construction-defined controls, human expert answer set으로 과장하지 않음
- [x] evaluator constructed-control accuracy 측정 — 완전 qualification 기록 9건 재감사, gate PASS 9/9
- [x] 반복 평가 일치도 측정 — 376 decisions, 관찰 범위 375/376~376/376
- [x] boundary/disagreement case 분석 — `electric:mitigation-unsafe / mitigation_specific` 1건 확인
- [x] provider 비결정성으로 인한 변동 범위 측정 — mitigation 99.21875~100%, decision stability 99.73404~100%
- [x] evaluator 변경 시 재qualification 조건 정의
- [x] `08_EVALUATOR_SPECIFICATION.md`, `09_EVALUATOR_QUALIFICATION.md` 작성
- [ ] 시험 직전 live AJQG 재실행 — 2026-10-11 현재 `.env` OpenAI credential 인증 실패(401), credential 갱신 후 실행

**완료 조건:** Judge가 왜 측정도구로 사용할 수 있는지 별도 근거가 존재하고, 시험 직전 동일 frozen gate를 다시 통과한다.

**Phase 5 Drafts:** `08_EVALUATOR_SPECIFICATION.md`, `09_EVALUATOR_QUALIFICATION.md`
**현재 상태:** evaluator 구조·freeze·과거 적격성·반복안정성 증적은 `REVIEW` 수준으로 정리 완료. 공식 시험 직전 유효 credential로 live AJQG를 다시 실행하는 운영 항목만 남음.

## Phase 6. 재현 프로그램 패키지화

- [ ] clean-room 실행 가능한 evaluator/runner entrypoint 정의
- [ ] 설정 파일과 secret 파일 분리
- [ ] dependency lock 확인
- [ ] 설치 명령 정의
- [ ] GT 로드 시 hash validation 구현 또는 확인
- [ ] SUT version preflight 확인 구현 또는 확인
- [ ] API health/auth preflight 구현
- [ ] deterministic ordering 및 run ID 생성 규칙 정의
- [ ] raw input/output 자동 보존
- [ ] 중간 판정 결과 보존
- [ ] 최종 metric 자동 계산
- [ ] 실행 종료 시 manifest 생성
- [ ] 실패/재시도 로그 보존
- [ ] example run 제공
- [ ] `10_REPRODUCIBILITY_GUIDE.md` 작성

**완료 조건:** 새 환경에서 README/가이드만 보고 end-to-end 시험이 실행된다.

## Phase 7. API 접근 및 권한 인계

- [ ] 시험기관 전용 계정/credential 전략 결정
- [ ] 최소권한 scope 정의
- [ ] credential 유효기간/회수 절차 정의
- [ ] 실제 secret은 Git/HWP에서 분리
- [ ] base URL 및 endpoint 기록
- [ ] authentication sequence 기록
- [ ] sample request/response 작성
- [ ] timeout/rate limit/retry/error code 설명
- [ ] 시험 중 운영환경 변경 금지 또는 변경 통지 절차 정의
- [ ] `11_API_ACCESS_GUIDE.md` 작성

**완료 조건:** 시험기관이 별도 개발자 지원 없이 인증 후 API를 호출할 수 있다.

## Phase 8. 무결성·버전·변경통제

- [ ] 제출대상 파일 최종 목록 생성
- [ ] 모든 canonical 파일 SHA-256 계산
- [ ] repo SHA 및 tag/release 기록
- [ ] GT/evaluator/prompt/schema 각각 별도 version 부여
- [ ] 생성 시각과 생성 도구 기록
- [ ] manifest 자체의 무결성 보장 방식 결정
- [ ] freeze 이후 변경 승인 절차 정의
- [ ] 변경 발생 시 영향분석 및 재시험 범위 정의
- [ ] `13_INTEGRITY_MANIFEST.md`, `14_CHANGE_CONTROL.md` 작성

**완료 조건:** 제출 이후 어떤 파일이 하나라도 바뀌면 탐지할 수 있고 변경 책임/재시험 범위를 판단할 수 있다.

## Phase 9. Clean-room 재현성 시험

- [ ] 기존 개발환경과 분리된 환경 준비
- [ ] 문서만 보고 설치/인증 수행
- [ ] preflight 실행
- [ ] sample subset 실행
- [ ] full run 실행
- [ ] 원 측정 결과와 비교
- [ ] 결과 차이가 있으면 원인 분류(model nondeterminism / config / code / data / provider)
- [ ] 허용 가능한 반복 변동 기준 정의
- [ ] 제3자 또는 작업에 관여하지 않은 내부 연구자가 문서만 보고 재현
- [ ] 발견된 문서 누락 수정
- [ ] 최종 reproducibility sign-off

**완료 조건:** 작성자가 직접 개입하지 않아도 재현 가능하다.

## Phase 10. 공문형 HWP/HWPX 작성

- [ ] 기관 제공 양식 존재 여부 확인 — 존재하면 해당 양식을 최우선 적용
- [ ] 제출 문서의 문서번호/수신/참조/제목/발신/결재 체계 확인
- [ ] `HWP_HANDOFF_SPEC.md`에 따라 본문 구조 확정
- [ ] Markdown의 `{{PLACEHOLDER}}` 잔여 항목 전수 점검
- [ ] 표/그림/별첨 번호 재정렬
- [ ] 본문과 별첨 간 cross-reference 검증
- [ ] 버전·SHA·날짜가 manifest와 일치하는지 검증
- [ ] secret/API key가 HWP에 포함되지 않았는지 검증
- [ ] HWP/HWPX 생성
- [ ] PDF preview 생성 후 레이아웃 검수
- [ ] 페이지 번호/머리말/꼬리말/표 잘림/폰트 대체 검수
- [ ] 연구책임자/검토자/승인자 내부 검토
- [ ] 최종 HWP/HWPX와 PDF preview hash 계산
- [ ] 최종 제출본 승인

**완료 조건:** 다른 에이전트가 Markdown과 증적만 보고 임의 추정 없이 HWP를 재생성할 수 있고, 제출본이 내부 승인됨.

## Phase 11. 기관 인계 및 시험 지원

- [ ] 제출 파일 목록과 수량 확인
- [ ] 일반자료 전달 채널 확정
- [ ] credential/secret 별도 전달
- [ ] 시험기관 담당자에게 실행 순서 안내
- [ ] credential 활성화 확인
- [ ] 시험기간 중 변경 freeze 확인
- [ ] 기관 재현 결과 수령
- [ ] discrepancy 발생 시 raw artifact 기준 비교
- [ ] 최종 시험 종료 후 credential 회수
- [ ] 최종 기관 피드백과 수정이력 보관

## 작업 규칙

- 체크박스를 완료할 때는 가능하면 바로 아래에 `Evidence:`와 실제 파일 경로/commit SHA/run ID를 기록한다.
- 기존 채팅에서 기억한 값은 `확정값`으로 취급하지 않는다.
- provider UI에서 보이는 `Sol`, `fast` 등의 제품명과 API가 실제 노출하는 model identifier를 구분한다.
- temperature처럼 모델/API에서 제어할 수 없는 값은 숫자를 만들어 넣지 않는다.
- 전문가 신뢰도 통계는 데이터 유형을 확인한 뒤 적절한 방법을 선택한다. 특정 통계를 먼저 정해 놓고 데이터를 끼워 맞추지 않는다.
- 시험기관 요구와 내부적으로 더 엄격하게 관리하는 항목을 문서에서 구분한다.
- HWP 편집자가 기술적 내용을 재해석하지 않도록 Markdown 본문은 최종 문장 수준으로 작성한다.
