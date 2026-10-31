# kolas-llm-judge

SEEXR 위험성평가 시스템의 KOLAS 시험 대응을 위한 독립 LLM-as-Judge 평가 하네스입니다.

## 구현 상태

- [x] 시험 규격 draft v0.5
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
- [x] 실행 전/후 인증된 SUT API 계약 상태 비교 (`GET /agents`) — 외부 API 계약 검증이며 운영 서버의 소스 커밋 증빙과는 별개
- [x] legacy ordinal human calibration template/gate (research compatibility)
- [x] official Boolean blinded Human–LLM calibration template/gate under `derived/`
- [x] Judge repeatability runner
- [x] smoke / pilot / full batch runner with case/stage/retry/elapsed/ETA progress
- [x] full run calibration gate 강제
- [x] JSON / CSV canonical report exporter
- [x] SUT retry/SSE reconnect with idempotent clientRequestId
- [x] SUT latency/retry + Judge token/call usage statistics
- [x] SHA-256 run seal / tamper verification
- [x] 104-control Automatic Judge Qualification Gate (AJQG)
- [x] binary-checklist Judge (`binary-checklist-v1`)
- [x] bounded case/SUT/Judge parallel worker pool
- [x] concurrency-safe rotating auth refresh
- [x] automated SUT/evaluator/infrastructure failure taxonomy
- [x] automated official report / manifest / source recheck
- [x] `official-live` one-command orchestrator + live dashboard + seal/verify
- [ ] 시험기관 확정 양식의 공식 XLSX 패키징
- [x] live 10-case smoke 실행 및 two-stage 병목 검증
- [ ] corrected-contract smoke / pilot / full 실행

## KOLAS official automated path

**Monitoring presentation policy:** CLI progress and result screens show HIA (Hazard Identification Accuracy) as the only performance KPI, plus operational status, validation failures, and artifact paths. All other metrics (semantic recall, coverage, schema compliance, Judge qualification/calibration details, token usage, etc.) remain computed and stored unmodified in JSON/CSV evidence. This display-only policy applies to smoke, pilot, official-live, derived and repeatability monitoring; do not suppress failures or weaken official gates.

KOLAS 현장 시험용 경로는 multi-day human calibration을 요구하지 않습니다. 시험 시작 시 construction-defined 104-control **Automatic Judge Qualification Gate (AJQG)** 를 자동 실행하고, PASS한 frozen binary-checklist Judge만 본시험에 사용합니다.

Judge 적격성 시험만 실행:

    /home/pikaybh/.local/bin/uv run --env-file .env kolas-llm-judge qualify-judge

시험 당일 one-click 전체 실행:

    /home/pikaybh/.local/bin/uv run --env-file .env kolas-llm-judge official-live

`official-live`는 **preflight → AJQG → 425-case bounded parallel evaluation → production source fingerprint 재검증 → report → SHA-256 seal → self-verification**을 자동 수행합니다. 공식 모드에서는 case 일부 실행이나 AJQG skip을 허용하지 않습니다.

공식 runtime은 `configs/official_runtime_v1.yaml`에 freeze되어 있습니다: **case queue 24 / SUT 6 / Judge 12 / GPT-5.6 Sol medium**. 50-case production load test에서 255.38초, SUT p95 36.72초, retry/reconnect/auth recovery 0, source stable, procedure valid, seal verified를 확인했습니다. 공식 모드에서는 CLI/.env의 model·concurrency·chunk·SUT-method override를 무시하며 `.env`는 자격증명만 제공합니다. dataset/AJQG seed·gate·control/binary prompt·rubric SHA도 runtime에 고정됩니다.

병렬 처리량 개발 benchmark 예시:

    /home/pikaybh/.local/bin/uv run --env-file .env kolas-llm-judge official-live --development --case-limit 10 --skip-qualification

실패는 자동 분류합니다. `sut_non_completion`(예: `<ask_user>`, 누락/비정상 risk XML)은 제품의 completion 측정값으로 남기되 시험 절차 자체를 무효화하지 않습니다. `evaluator_failure` 또는 retry 후 지속되는 `infrastructure_failure`는 official candidate를 무효화합니다.

현재 AJQG v1은 8개 대표 위험에서 104개 control을 생성하며 control-suite SHA-256, family별 정확도, structured completion, 반복 안정성을 JSON/CSV로 기록합니다.

시험 전 독립 Human–LLM 검증이 필요한 경우에는 official Boolean Rubric 그대로 blinded 표본을 생성합니다. 이 경로는 **official-live의 필수 gate가 아니며**, sealed source run을 수정하지 않고 `derived/binary_calibration/<run_id>/`에만 산출물을 둡니다.

```bash
uv run kolas-llm-judge make-binary-calibration <SEALED_RUN_ID>
# 독립 전문가 라벨링은 현 제출 범위에 포함되지 않으며 별도 협의 시에만 사용
uv run kolas-llm-judge score-binary-calibration <SEALED_RUN_ID>
```

생성 manifest는 source run manifest SHA-256, source run seal root SHA-256, 각 CSV의 비라벨 sample identity SHA-256을 고정합니다. Judge 값은 인간 라벨링 CSV에 노출되지 않습니다.

## Setup

    /home/pikaybh/.local/bin/uv sync
    cp .env.example .env

`.env`에는 다음 두 종류의 credential이 필요합니다.

1. OpenAI Judge: `OPENAI_API_KEY`
2. SEEXR SUT: 별도 전달받은 운영 전용 `SEEXR_API_KEY` (HTTP `x-api-key`)

공식 KOLAS 실행은 **Blue 운영 서버(`https://api.seexr.co.kr/api`) + SEEXR_API_KEY만** 허용합니다. 키 발급 절차는 시험기관이 수행하지 않습니다. 운영 배포와 키가 준비되기 전에는 본시험을 실행하지 않습니다. 키 실패 시 다른 인증 방식으로 우회하지 않습니다.

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

## Legacy / FACE research execution sequence

아래 0–4/0–2 ordinal human calibration 기반 흐름은 학술/FACE/기존 연구 호환용으로만 보존합니다. KOLAS official v1의 Boolean Human–LLM 검증은 위 `make-binary-calibration` / `score-binary-calibration`을 사용하고, 시험 당일 필수 경로는 `official-live` + AJQG입니다.

### 1. 10-case smoke

    /home/pikaybh/.local/bin/uv run kolas-llm-judge run --mode smoke

### 2. 50-case pilot

Pilot은 전체 성능 추정용 random sample이 아니라 **Judge calibration / edge-case 노출용 process-diversity sample**입니다. baseline 168개 공정 중 서로 다른 50개 공정을 deterministic하게 선택하고, 각 공정에서는 중앙 위치 scenario를 대표 case로 사용합니다. 최종 모집단 성능은 425-case full에서 계산합니다.

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

## Reuse an existing run for identification analysis

Persisted `binary_judge.json` match matrices can be re-used without any new LLM calls:

```bash
uv run kolas-llm-judge derive-identification <RUN_ID>
```

The command writes a derived JSON artifact under `derived/` and does not modify the sealed
source run. It reports both:

- `hazard_identification_accuracy`: KPI-oriented many-to-one identification using
  `(same_hazard_mechanism AND context_compatible) OR accident_compatible`
- `strict_reference_risk_coverage_1to1`: the original strict Hungarian 1:1 coverage

The official runtime freezes the identification rule and denominator so future official runs
cannot silently change the metric definition.

## Final KOLAS packaging

현재 JSON/CSV를 canonical frozen result로 사용합니다.
시험기관이 요구하는 최종 XLSX/보고서 양식을 확정하면 동일 frozen artifact에서
별도 생성합니다. 평가 로직과 제출 양식을 분리하여 보고서 형식 변경이 시험 결과를
바꾸지 않도록 합니다.

시험 실행 방법은 본 README와 `configs/official_runtime_v1.yaml`을 참조하세요. 내부 기술 문서는 별도 관리합니다.

## KOLAS compliance hardening (2026-09-14)

The lab-facing method is now explicitly separated from legacy project KPI semantics:

- **Proposed KOLAS primary:** `hazard_identification_accuracy` = `(same_hazard_mechanism AND context_compatible) OR accident_compatible` at reference level.
- **Secondary diagnostic:** `hazard_semantic_identification_recall` = `same_hazard_mechanism AND context_compatible`. No post hoc scoring-rule change. Final acceptance requires laboratory agreement.
- Product pass/fail thresholds remain **unfrozen pending testing-lab approval**; procedure-validity gates are frozen independently.
- `compare-repeatability` compares two or more equivalent sealed live runs and reports aggregate, per-case, and per-reference semantic stability.
- Dataset identity is explicit: `KOLAS_RA_GT` v1.0.0 / `kolas-ra-dataset-v1`.

Lab-facing documents:

- `docs/testing_lab_method_and_rubric_v1.md`
- `docs/kolas_compliance_plan_v1.md`
- `docs/email_draft_to_kang_sungdae.md` (15단계 최종 행정 산출물; 내부 검증 완료 후 마지막으로 갱신)
