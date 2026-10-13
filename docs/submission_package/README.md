# KOLAS 재현성·GT 검증상태·시험기관 제출 패키지

> 이 디렉토리는 SEEXR 위험성평가 AI의 KOLAS 시험 대응을 위한 **영구 기준 문서**다.
> GitHub Issue는 진행 상황을 추적하는 작업 원장이고, 시험방법·고정값·GT 근거·재현절차·HWP 편집 기준의 최종 기준은 이 디렉토리에 남긴다.

- GitHub 작업 원장: `pikaybh/kolas-llm-judge#1`

## 1. 목표

최종 목표는 단순 성능 보고서가 아니라, 외부 시험기관이 SEEXR이 사용한 것과 **동일한 GT, 동일한 측정 시스템, 동일한 SUT 버전, 동일한 모델/추론 설정, 동일한 판정 규칙**을 사용하여 시험을 재현할 수 있는 제출 패키지를 만드는 것이다.

제출 패키지는 다음 질문에 문서와 증적으로 답할 수 있어야 한다.

1. 무엇을 시험했는가?
2. 어떤 시스템 버전과 API를 시험했는가?
3. 어떤 모델과 추론 설정을 사용했는가?
4. GT는 왜 정답지로 사용할 수 있는가?
5. GT의 각 항목은 어떤 출처에 근거하는가?
6. GT가 연구실 구성원들의 검토를 거쳐 이미 검증된 데이터임을 어떻게 명시할 것인가?
7. GT가 연구실 구성원의 검토를 거쳐 검증된 데이터라는 사실을 제출문서에서 어떻게 명확히 기록하는가?
8. LLM Judge를 포함한 측정 시스템은 어떻게 고정·검증되었는가?
9. 외부 시험기관이 같은 시험을 어떤 명령과 권한으로 재실행하는가?
10. 제출 이후 파일·설정·코드가 바뀌지 않았음을 어떻게 증명하는가?

## 2. 핵심 원칙

- **재현성 우선**: 성능 수치만 남기지 않고 수치를 생성한 전체 측정 체인을 고정한다.
- **추측 금지**: 실제 코드·API 응답·공식 문서에서 확인되지 않은 모델 파라미터나 시스템 동작을 사실처럼 기재하지 않는다.
- **GT 검증과 provenance 구분**: GT는 연구실 구성원 검토를 거쳐 검증된 데이터로 취급하며, 원작성 source provenance는 별도의 traceability 정보로 관리한다.
- **버전 고정**: SUT, GT, evaluator, prompt, schema, dependency, API contract를 명시적 버전 또는 commit SHA로 묶는다.
- **무결성 보장**: 최종 제출물과 핵심 중간 산출물에 SHA-256을 기록한다.
- **비밀정보 분리**: API key, password, refresh token 등 실제 secret은 Git/HWP에 넣지 않는다. 문서에는 발급·전달·권한 범위만 명시한다.
- **원시 증적 보존**: 최종 점수만이 아니라 scenario input, raw SUT output, raw Judge output, 판정 결과, 계산 결과를 추적 가능하게 보존한다.
- **변경 통제**: freeze 이후 변경은 새 버전으로 취급하고 변경 사유와 영향 범위를 기록한다.

## 3. 최종 산출물 형태

내부 작성·검증은 Markdown/CSV/JSON/XLSX/코드로 수행한다. 외부 제출용 최종 문서는 **대한민국 공문 형태의 HWP/HWPX**로 편집한다.

Markdown은 메모가 아니라 HWP 편집을 위한 **문서 중간 표현(Intermediate Representation)** 으로 취급한다. 따라서 모든 본문 문서는 다음을 명시해야 한다.

- 문서 ID / 제목 / 버전 / 상태 / 작성·검토·승인 상태
- 본문에 들어갈 최종 문장
- 표 번호와 표 제목
- 그림 번호와 그림 제목
- 별첨 번호와 별첨 파일명
- 근거 파일 또는 evidence ID
- 아직 확정되지 않은 값은 `{{PLACEHOLDER_NAME}}` 형식
- 보안상 별도 전달하는 값은 `[별도 보안채널 제공]`으로 표기

상세 HWP 편집 규칙은 [`HWP_HANDOFF_SPEC.md`](./HWP_HANDOFF_SPEC.md)를 따른다.

## 4. 문서 구성

상세 목록과 상태는 [`DOCUMENT_REGISTER.md`](./DOCUMENT_REGISTER.md)에서 관리한다. 현재 계획하는 본문 문서는 다음과 같다.

1. `01_TEST_METHOD.md` — 시험 목적, 범위, 지표, 계산식, 판정 흐름
2. `02_SYSTEM_UNDER_TEST.md` — 시험대상 시스템 구성과 버전
3. `03_INFERENCE_CONFIGURATION.md` — 모델, reasoning/fast mode, sampling/runtime 설정
4. `04_GT_SPECIFICATION.md` — GT 스키마, 범위, freeze 규칙
5. `05_GT_SOURCE_PROVENANCE.md` — GT 출처와 추적 체계
6. `06_EXPERT_VALIDATION_PROTOCOL.md` — **작성 불필요**; GT는 기존 연구실 검증 완료 사실만 본문에 기록
7. `07_GT_RELIABILITY_REPORT.md` — **작성 불필요**; 확인되지 않은 일치도/신뢰도 통계를 신규 생성하지 않음
8. `08_EVALUATOR_SPECIFICATION.md` — semantic Judge 및 판정 알고리즘
9. `09_EVALUATOR_QUALIFICATION.md` — evaluator 자체 검증 결과
10. `10_REPRODUCIBILITY_GUIDE.md` — 외부기관 재실행 절차
11. `11_API_ACCESS_GUIDE.md` — API 접속, 인증, 권한, 오류/재시도
12. `12_VERSION_MANIFEST.md` — repo별 SHA, dependency, prompt/schema version
13. `13_INTEGRITY_MANIFEST.md` — SHA-256 및 제출 파일 목록
14. `14_CHANGE_CONTROL.md` — freeze 이후 변경통제
15. `15_TEST_DATA_INDEPENDENCE_AUDIT.md` — GT와 SUT 학습/runtime retrieval knowledge 중복 감사
16. `16_EXECUTION_ENVIRONMENT_REPEAT_POLICY.md` — HW/SW 환경과 반복시험 신규생성·세션·캐시 정책
17. `17_KOLAS_REQUEST_CROSSWALK.md` — 시험기관 요청사항별 답변·증적 위치 one-stop index

## 5. 작업 상태

- 전체 진행 계획: [`MASTER_PLAN.md`](./MASTER_PLAN.md)
- Phase 0 증적 등록부: [`00_PHASE0_EVIDENCE_INVENTORY.md`](./00_PHASE0_EVIDENCE_INVENTORY.md)
- Phase 0 감사 로그: [`00_PHASE0_AUDIT_LOG.md`](./00_PHASE0_AUDIT_LOG.md)
- HWP 편집/인수인계 명세: [`HWP_HANDOFF_SPEC.md`](./HWP_HANDOFF_SPEC.md)
- 문서 등록부: [`DOCUMENT_REGISTER.md`](./DOCUMENT_REGISTER.md)
- 섹션 작성 템플릿: [`templates/SECTION_TEMPLATE.md`](./templates/SECTION_TEMPLATE.md)
- SUT freeze candidate: [`SUT_FREEZE_CANDIDATE.md`](./SUT_FREEZE_CANDIDATE.md)
- 시험기관 method decision register: [`LAB_METHOD_DECISION_REGISTER.md`](./LAB_METHOD_DECISION_REGISTER.md)
- 최종화 blocker register: [`FINALIZATION_BLOCKER_REGISTER.md`](./FINALIZATION_BLOCKER_REGISTER.md)
- HWP assembly map: [`HWP_ASSEMBLY_MAP.md`](./HWP_ASSEMBLY_MAP.md)
- placeholder audit: [`PLACEHOLDER_AUDIT.md`](./PLACEHOLDER_AUDIT.md)

현재 이 repository에는 이미 KOLAS 평가 하네스, `KOLAS_RA_GT v1.0.0`, frozen Boolean Rubric, official runtime, AJQG, live SUT 실행, repeatability, seal/verify 및 시험기관 협의용 문서가 구현되어 있다. 따라서 본 계획은 시스템을 처음 만드는 계획이 아니라 **기존 구현을 canonical evidence로 감사하고, 시험기관의 재현성 요구를 충족하고, 이미 연구실에서 검증된 GT의 상태와 evaluator 적격성 근거를 제출자료로 정리하는 계획**이다.

기존 대화에서 알려진 수치나 설정은 초안 참고사항일 뿐이며, 공식 제출 문서에는 반드시 이 repository의 코드·manifest·sealed run·원본 데이터와 SUT repository/API 설정을 대조한 값만 기입한다.

## 6. 다음 에이전트가 작업을 이어받는 방법

1. 이 `README.md`를 읽는다.
2. [`MASTER_PLAN.md`](./MASTER_PLAN.md)의 `현재 재개 지점`을 확인한다.
3. GitHub의 KOLAS 마스터 이슈 체크박스와 이 문서의 체크박스를 비교한다.
4. 시작 전 해당 repository의 `git status`, `git diff`, upstream 상태를 확인한다.
5. 완료한 단계는 **증적 경로 또는 commit SHA와 함께** 체크한다.
6. 기억이나 이전 채팅만으로 값/수치를 채우지 않는다.
7. 작업 중 새 결정이 생기면 해당 본문 문서와 변경통제 문서에 남긴다.
8. HWP 생성 단계에서는 `HWP_HANDOFF_SPEC.md`를 반드시 읽고, `{{PLACEHOLDER}}`를 임의로 추정해서 채우지 않는다.

## 7. 완료의 정의

이 작업은 다음이 모두 충족될 때 완료된 것으로 본다.

- GT가 연구실 검증 완료 상태로 명시되고 canonical content/hash가 freeze됨
- GT가 연구실 구성원들의 검토를 거쳐 이미 검증된 데이터임이 문서에 명시됨
- SUT/evaluator/model/prompt/config가 모두 특정 버전으로 freeze됨
- 외부기관이 신규 환경에서 시험 전체를 재현할 수 있음
- 실행 결과부터 원시 응답까지 역추적 가능함
- 최종 제출 파일 전체에 integrity manifest가 존재함
- HWP/HWPX 공문 본문과 별첨이 생성되고 내부 검토를 통과함
- 실제 secret을 제외한 재현 패키지가 인계 가능함
