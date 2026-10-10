# KOLAS 재현성 패키지 마스터 계획

- 문서 ID: `KOLAS-PLAN-001`
- 상태: `IN_PROGRESS`
- 목적: 작업이 중단되어도 다른 에이전트가 동일한 기준으로 즉시 재개할 수 있는 작업 원장
- 최종 산출물: 공문형 HWP/HWPX + 별첨 재현 패키지
- GitHub 작업 원장: `pikaybh/kolas-llm-judge#1`

## 현재 재개 지점

> **Phase 0 — 기존 구현과 증적을 제출 기준으로 재감사하는 단계부터 시작한다.**
> 이 repository에는 이미 `configs/official_runtime_v1.yaml`, `KOLAS_RA_GT v1.0.0`, frozen Rubric/prompt, evaluator 코드, official-live/반복성/seal 관련 산출물이 존재한다. 새로 만드는 것이 아니라 **현재 구현을 evidence ID와 제출문서 항목에 연결하고, GT provenance 및 전문가 3인 이상 검증 등 부족한 부분을 식별·보강**한다.

## Phase 0. 기존 자료 및 구현 재감사 / Evidence Inventory

- [ ] 현재 repository의 KOLAS 코드·스크립트·GT·sealed run·derived 결과·문서 위치를 evidence inventory로 등록
- [ ] `KOLAS_RA_GT v1.0.0`의 425 scenarios / 843 reference hazards canonical 원본·manifest·hash 재확인
- [ ] 과거 실행 결과(예: broad/strict semantic 평가)가 생성된 실제 스크립트와 raw 결과 확인
- [ ] 현재 SUT 호출 경로(`seexr-api-core` → agents/RA 등) 실제 코드 기준 정리
- [ ] 현재 사용 모델을 agent별로 코드/환경설정/API 요청 기준 확인
- [ ] 모델 provider가 실제로 허용하는 추론 파라미터 목록 확인
- [ ] temperature/top_p/seed/reasoning effort 등 각 파라미터의 `고정/미사용/미지원/provider-controlled` 상태 확인
- [ ] system/user prompt 및 structured-output schema의 실제 소스 위치 확인
- [ ] retry/timeout/concurrency/rate-limit 정책 확인
- [ ] 기존 evaluator/Judge 구현, `judge_binary_v1.md`, `rubric_binary_v1.yaml`, official runtime freeze의 정합성 재확인
- [ ] Git에 포함되지 않은 sealed run/raw artifact/전문가 자료 등 외부 증적과 보관 위치 조사
- [ ] 민감정보/개인정보가 제출 패키지에 섞일 가능성 점검
- [ ] 감사 결과를 `evidence inventory`로 작성

**완료 조건:** 모든 이후 문서에서 참조할 수 있는 파일 경로/commit SHA/evidence ID 목록이 존재한다.

## Phase 1. 시험 범위와 측정방법 Freeze

- [ ] 시험 목적과 대상 기능을 한 문장으로 확정
- [ ] 공식 측정 지표명 확정
- [ ] denominator/numerator 정의 확정
- [ ] scenario 단위와 reference hazard 단위 관계 정의
- [ ] semantic MATCH 조건 확정
- [ ] generated hazard atomic decomposition 규칙 확정
- [ ] 다수 generated hazard가 하나의 GT에 대응할 때 규칙 정의
- [ ] 하나의 generated hazard가 여러 GT에 대응할 때 규칙 정의
- [ ] SUT 실패/timeout/invalid schema 처리 규칙 정의
- [ ] 재시도 횟수와 실패가 metric에 반영되는 방식 정의
- [ ] 동일 입력 반복 시험 횟수 및 재현성 통계 정의
- [ ] 시험기관과 합의가 필요한 항목을 별도 표로 분리
- [ ] `01_TEST_METHOD.md` 승인본 작성

**완료 조건:** 동일 raw data를 주면 별도 해석 없이 같은 metric을 계산할 수 있다.

## Phase 2. SUT 및 추론 설정 Freeze

- [ ] 시험대상 제품 버전 부여
- [ ] 관련 repository별 commit SHA 기록
- [ ] API endpoint와 request/response schema version 기록
- [ ] agent별 모델 identifier 기록
- [ ] reasoning/fast/instant 등 provider mode를 실제 요청 기준 기록
- [ ] temperature/top_p/max tokens/seed 등 설정값 기록
- [ ] 설정 불가 값은 `미지원` 또는 `provider-controlled`로 명시
- [ ] prompt 파일 또는 prompt content hash 기록
- [ ] tool/function/schema 설정 기록
- [ ] dependency/runtime 버전 기록
- [ ] DB/schema/migration 상태 기록
- [ ] feature flag 및 환경변수 중 시험에 영향을 주는 값 목록화
- [ ] `02_SYSTEM_UNDER_TEST.md`, `03_INFERENCE_CONFIGURATION.md`, `12_VERSION_MANIFEST.md` 작성

**완료 조건:** 시험기관이 어떤 버전/모델/설정으로 호출해야 하는지 모호성이 없다.

## Phase 3. GT 정당성·출처·무결성 확립

- [ ] GT canonical 파일 결정
- [ ] GT schema와 필드 정의
- [ ] scenario/reference ID를 영구 ID로 고정
- [ ] duplicate/near-duplicate 점검
- [ ] 각 reference hazard의 source provenance 연결
- [ ] 법령/공공기관 자료/가이드/논문/현장자료 등 source type 정의
- [ ] 원문 인용 범위와 source locator(page/section/URL/document ID) 기록
- [ ] source의 라이선스/외부 제공 가능 여부 확인
- [ ] source가 없는 항목은 `expert-authored` 등으로 명시하고 별도 검토 강화
- [ ] GT 변경 이력 생성
- [ ] freeze candidate 생성
- [ ] GT 파일 SHA-256 계산
- [ ] `04_GT_SPECIFICATION.md`, `05_GT_SOURCE_PROVENANCE.md` 작성

**완료 조건:** 임의의 GT 항목 하나를 선택해도 근거 출처와 생성/수정 이력을 추적할 수 있다.

## Phase 4. 전문가 3인 이상 독립 검증

- [ ] 전문가 자격 기준 정의(연구/실무 경력, 전공, 이해상충 등)
- [ ] 최소 3인 검토자 확정
- [ ] 전문가별 소속/전문분야/경력 증빙 확보 방식 정의
- [ ] 독립평가용 blind form 제작
- [ ] 평가 문항과 척도 확정
- [ ] GT마다 `적합성`, `hazard mechanism 명확성`, `공정 맥락 적합성`, `중복 여부` 등 필요한 항목 정의
- [ ] 검토자 간 사전 상의 없이 1차 독립평가 실시
- [ ] missing/abstain 처리 규칙 정의
- [ ] 평가척도에 맞는 inter-rater reliability 통계 선택
- [ ] 단순 평균/일치율과 함께 Fleiss' κ, Krippendorff's α 등 적용 가능성 검토
- [ ] 신뢰구간 또는 불확실성 표현 방식 결정
- [ ] disagreement case 목록 생성
- [ ] consensus 회의 절차와 수정권한 정의
- [ ] consensus 전/후 결과 모두 보존
- [ ] 전문가 서명/확인서 확보
- [ ] `06_EXPERT_VALIDATION_PROTOCOL.md`, `07_GT_RELIABILITY_REPORT.md` 작성

**완료 조건:** `전문가가 검토했다`가 아니라 누가, 어떤 기준으로, 얼마나 일치했고, 불일치를 어떻게 해결했는지를 수치와 기록으로 제시할 수 있다.

## Phase 5. Evaluator / LLM Judge 측정시스템 검증

- [ ] evaluator 입력/출력 schema 확정
- [ ] Judge model identifier와 reasoning 설정 확정
- [ ] Judge prompt/rubric freeze
- [ ] Boolean 판정 로직 및 aggregation 로직 freeze
- [ ] control set 정의와 전문가 정답 확보
- [ ] evaluator accuracy 측정
- [ ] 반복 평가 일치도 측정
- [ ] boundary/disagreement case 분석
- [ ] provider 비결정성으로 인한 변동 범위 측정
- [ ] evaluator 변경 시 재qualification 조건 정의
- [ ] `08_EVALUATOR_SPECIFICATION.md`, `09_EVALUATOR_QUALIFICATION.md` 작성

**완료 조건:** Judge가 왜 측정도구로 사용할 수 있는지 별도 근거가 존재한다.

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
