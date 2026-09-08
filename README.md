# kolas-llm-judge

SEEXR 위험성평가 시스템의 KOLAS 시험 대응을 위한 독립 LLM-as-Judge 평가 하네스입니다.

## 구현 상태

- [x] 시험 규격 draft v0.4
- [x] uv / Python 3.12 독립 환경
- [x] legacy 843-row dataset importer
- [x] 843 reference -> 425 scenario builder
- [x] SUT/reference input leakage 방지
- [x] production risk_assessment XML parser
- [x] SUT mode-aware deterministic contract / range / score-math 검사
- [x] production SEEXR Core SUT client
- [x] token 또는 전용 non-admin 계정 자동 로그인
- [x] GPT-5.6 Sol Pydantic Structured Output Judge
- [x] two-stage Judge: match matrix → matched quality + generated safety
- [x] quality-independent deterministic 1:1 Hungarian matching
- [x] semantic / mitigation / legal / safety KPI aggregation
- [x] Wilson 95% CI 및 case macro statistics
- [x] atomic per-stage checkpoint and resume
- [x] immutable run manifest
- [x] production Core/Agents working-tree fingerprint 기록
- [x] 실행 전/후 SUT source stability 검증
- [x] human calibration template and calibration gate
- [x] Judge repeatability runner
- [x] smoke / pilot / full batch runner with case/stage/retry/elapsed/ETA progress
- [x] full run calibration gate 강제
- [x] JSON / CSV canonical report exporter
- [x] SUT retry/SSE reconnect with idempotent clientRequestId
- [x] SUT latency/retry + Judge token/call usage statistics
- [x] SHA-256 run seal / tamper verification
- [ ] 시험기관 확정 양식의 공식 XLSX 패키징
- [x] live 10-case smoke 실행 및 two-stage 병목 검증
- [ ] corrected-contract smoke / pilot / full 실행

## Setup

    /home/pikaybh/.local/bin/uv sync
    cp .env.example .env

`.env`에는 다음 두 종류의 credential이 필요합니다.

1. OpenAI Judge: `OPENAI_API_KEY`
2. SEEXR SUT:
   - smoke/development: `SEEXR_API_TOKEN` 또는 non-admin 계정
   - official pilot/full: 전용 non-admin 시험계정의 `SEEXR_EMAIL` + `SEEXR_PASSWORD`

현재 Core의 access token 기본 만료가 짧기 때문에 장시간 official run은 갱신 가능한 계정 로그인을 사용합니다.
하네스는 401 발생 시 메모리의 refresh token으로 자동 갱신하고, refresh가 실패하면 동일 non-admin
계정으로 재로그인합니다. access/refresh token은 artifact나 manifest에 저장하지 않습니다.
관리자 계정은 production MFA가 필요하므로 자동 시험계정으로 사용하지 않습니다.

Stage-1 match matrix는 기본 80 pair 단위로 분할하고 최대 3개 batch를 병렬 처리합니다.
감소대책/법규는 matching 이후 실제 matched pair에 대해서만 평가합니다.

    JUDGE_MAX_PAIRS_PER_CALL=80
    JUDGE_MAX_CONCURRENCY=3
    JUDGE_TIMEOUT_SECONDS=300
    JUDGE_MAX_RETRIES=3

SUT의 일시적 408/429/5xx 또는 transport 오류는 기본 3회까지 재시도합니다.
run 생성 재시도는 동일 `clientRequestId`를 사용하며, SSE 단절은 마지막 sequence부터 재연결합니다.

    SEEXR_MAX_RETRIES=3
    SEEXR_RETRY_BACKOFF_SECONDS=0.5

## Preflight

offline:

    /home/pikaybh/.local/bin/uv run kolas-llm-judge doctor

credential과 production API까지 확인:

    /home/pikaybh/.local/bin/uv run kolas-llm-judge doctor --live

공식 시험 직전에는 evaluation harness commit/clean 상태까지 확인합니다:

    /home/pikaybh/.local/bin/uv run kolas-llm-judge doctor --live --official --require-ready

## Dataset

    /home/pikaybh/.local/bin/uv run kolas-llm-judge import-dataset

Expected:

- source rows: 843
- scenarios: 425
- references: 843

SUT에는 공정, 세부공정, 원본에 명시된 설비, 물질/자재만 입력합니다.
유해위험요인, 사고분류, 위험도, 감소대책, 법규는 reference-only입니다.

## Recommended execution sequence

### 1. 10-case smoke

    /home/pikaybh/.local/bin/uv run kolas-llm-judge run --mode smoke

### 2. 50-case pilot

    /home/pikaybh/.local/bin/uv run kolas-llm-judge run --mode pilot

실행 id 확인:

    /home/pikaybh/.local/bin/uv run kolas-llm-judge list-runs

### 3. Human calibration

pilot 결과에서 human labeling template 생성:

    /home/pikaybh/.local/bin/uv run kolas-llm-judge make-calibration PILOT_RUN_ID

동일 frozen Judge 반복성 측정:

    /home/pikaybh/.local/bin/uv run kolas-llm-judge judge-repeatability PILOT_RUN_ID

두 명의 안전전문가가 `human_pairs.csv`, `human_quality_pairs.csv`, `human_generated.csv`를
독립적으로 평가하고 불일치를 adjudication한 뒤:

    /home/pikaybh/.local/bin/uv run kolas-llm-judge score-calibration PILOT_RUN_ID

`human_pairs.csv`는 Stage-1 semantic/사고유형, `human_quality_pairs.csv`는 실제 matched pair의
감소대책 적합성/구체성/법규 관련성, `human_generated.csv`는 unsupported claim과 critical safety error를 검증합니다.

기본 calibration gate:

- semantic Judge-human binary agreement >= 0.90, Cohen kappa >= 0.70
- 사고유형 및 matched-quality 차원 agreement >= 0.85, Cohen kappa >= 0.60
- unsupported / critical safety boolean agreement >= 0.90
- overall 및 차원별 repeatability >= 0.95 (`match_assignment` 포함)
- structured-output completion >= 0.99
- human label completion = 1.00
- match/quality/generated 각 적용 차원별 유효 sample >= 30

calibration 결과에는 pilot의 dataset/code/prompt/rubric/Judge 설정과 SUT endpoint/agent/
위험성평가 방식/model mode/reasoning style을 고정합니다. full run에서 어느 하나라도 달라지면
gate가 PASS여도 실행이 차단됩니다.

### 4. 425-case full official candidate

통과한 calibration run을 명시해야 합니다.

    /home/pikaybh/.local/bin/uv run kolas-llm-judge run --mode full --calibration-run PILOT_RUN_ID

calibration gate가 없거나 FAIL이면 full 실행은 차단됩니다.

개발 중에만 강제 실행할 수 있습니다.

    /home/pikaybh/.local/bin/uv run kolas-llm-judge run --mode full --allow-uncalibrated-full

이 override 결과는 official candidate로 취급하지 않습니다.

## Resume

중단된 동일 run을 이어서 실행:

    /home/pikaybh/.local/bin/uv run kolas-llm-judge run --mode pilot --run-id RUN_ID

각 case는 별도로 다음 checkpoint를 저장합니다.

- `sut.json`
- `parsed.json`
- `judge.json`
- `result.json`
- 실패 시 `error.json`

예를 들어 Judge 단계에서 중단되면 이미 완료된 production SUT 호출은 다시 하지 않습니다.

단, 기존 manifest와 현재 dataset, prompt/rubric, evaluation source 또는
production Core/Agents fingerprint가 다르면 resume을 차단합니다.

## Official candidate validity

full report의 `official_candidate_valid`는 아래 조건을 전부 만족해야만 `true`입니다.

- 425 case 전부 완료
- failed case 0
- calibration gate PASS
- full method identity = calibration frozen method identity
- full SUT evaluation identity = calibration pilot SUT identity
- 실행 시작/종료 production Core/Agents relevant source fingerprint 동일
- calibration source evaluator와 full evaluator 모두 committed + clean

production repos의 전체 dirty 상태는 감사 정보로 남기지만, official stability는
위험성평가 실행 관련 source scope의 content hash로 판정합니다. 따라서 SUS/admin/결제처럼
시험 대상과 무관한 소스 변경은 시험 자체를 불필요하게 무효화하지 않습니다.

## Reports

    /home/pikaybh/.local/bin/uv run kolas-llm-judge report RUN_ID

Canonical artifacts:

- `report/summary.json`
- `report/case_metrics.csv`
- `report/failures.csv`
- case별 raw/checkpoint JSON
- immutable `manifest.json`
- `completion.json`
- full run의 `run_seal.json`

Aggregate report에는 주요 비율의 numerator/denominator/rate,
Wilson 95% CI, case macro mean/std가 포함됩니다. 추가로 SUT latency mean/median/p95,
재시도 및 SSE 재연결 통계, Judge call/input/output/total/reasoning/cached token 합계를 기록합니다.

법규는 다음 두 지표로 분리합니다.

- `legal_basis_presence`: matched risk 중 법규가 실제 제공된 비율
- `legal_basis_relevance`: 법규가 제공된 matched risk 중 직접 관련된 비율

결정론 검사는 SUT model mode의 실제 production contract를 따릅니다. `fast`에서는
`post_improvement_*` 태그의 존재+빈 값을 검증하고 개선후 산술 지표는 N/A로 기록합니다.
그 외 formatter 경로에서는 개선후 빈도/강도 범위, 점수 산술 일치, 위험도 비증가를 검증합니다.

full run 종료 후 artifact는 자동 seal됩니다. 필요하면 수동으로 다시 봉인하거나 검증할 수 있습니다.

    /home/pikaybh/.local/bin/uv run kolas-llm-judge seal RUN_ID
    /home/pikaybh/.local/bin/uv run kolas-llm-judge verify RUN_ID

`verify`는 파일 누락, 내용 변경, 예상하지 않은 추가 artifact, root digest 불일치를 탐지합니다.

## Final KOLAS packaging

현재 JSON/CSV를 canonical frozen result로 사용합니다.
시험기관이 요구하는 최종 XLSX/보고서 양식을 확정하면 동일 frozen artifact에서
별도 생성합니다. 평가 로직과 제출 양식을 분리하여 보고서 형식 변경이 시험 결과를
바꾸지 않도록 합니다.

자세한 시험 프로토콜은 `docs/evaluation_spec.md`를 참조하세요.
