# SEEXR KOLAS LLM-as-Judge Evaluation Specification

Status: draft v0.2 (시험기관 협의 전)
Scope: app.seexr.dev 위험성평가 생성 결과의 정량 평가
Dataset baseline: legacy KOLAS accident evaluation v7_73 test set

## 1. 목적

기존 사고분류 label-intersection accuracy를 대체하여 현재 SEEXR가 생성하는
전체 위험성평가의 의미적 품질, 구조적 일관성, 안전 오류를 재현 가능하고
감사 가능한 방식으로 측정한다.

시험 러너는 production SEEXR와 분리된 독립 측정 도구로 운영한다.
LLM Judge는 의미 판단만 담당하고 산술, 허용범위, 출력 완전성처럼
결정론적으로 계산 가능한 항목은 Python evaluator가 담당한다.

## 2. 시험 단위

원본 843개 reference risk row를 공정 + 세부공정으로 묶어 scenario를 구성한다.
baseline dataset은 425개 scenario, 843개 reference risk로 고정한다.

### SUT 입력

- 공정
- 세부공정
- 해당 scenario의 원본 데이터에 명시된 설비 목록
- 해당 scenario의 원본 데이터에 명시된 물질/자재 목록

### Reference only - SUT 입력 금지

- 유해위험요인
- 사고분류
- 위험 가능성
- 위험 중대성
- 위험성
- 감소대책
- 관련근거(법규)

각 case는 별도 production chat session에서 실행한다. SUT 입력 payload에
reference-only 필드가 포함되지 않도록 scenario builder와 테스트에서 검증한다.

## 3. 평가 분리 원칙

### Deterministic evaluator

- risk_assessment XML parse 성공 여부
- 필수 위험 항목 필드 존재 여부
- 빈도강도법 5x4, 4x3, 3x3의 빈도/강도 허용범위
- 초기 위험도 = 빈도 x 강도 산술 일관성
- 개선 후 빈도/강도 허용범위
- 개선 후 위험도 = 개선 후 빈도 x 개선 후 강도 산술 일관성
- 개선 후 위험도 <= 초기 위험도
- 3단계 판단법/체크리스트법의 상/중/하 값 유효성 및 개선 후 비증가
- API 성공/실패, latency, retry/SSE reconnect, checkpoint 상태

### LLM Judge

- reference 위험요인과 generated 위험요인의 의미적 일치
- 사고유형 적합성
- 감소대책 적합성
- 감소대책 구체성
- 제공된 법규의 위험/대책 관련성
- generated risk의 입력/안전지식 근거 없음 여부
- 치명적 안전 오류 여부

LLM Judge는 위험도 수치 계산이나 범위 검사를 추정하지 않는다.

## 4. Judge structured output 및 chunking

Judge는 Pydantic Structured Outputs로 스키마를 강제한다.
모든 reference-generated pair와 모든 generated risk가 정확히 한 번씩
평가됐는지 Python에서 완전성을 검증하며 누락/중복이 있으면 case를 실패시킨다.

pair 수가 설정된 한도 이하이면 case당 한 번의 structured call을 사용한다.
한도를 초과하는 큰 case는 reference-generated pair matrix를 고정 크기로
분할하고 generated-only 안전 판정을 별도 call로 수행한다. 모든 batch를
합친 뒤 전체 pair matrix를 다시 검증한다.

기본 max_pairs_per_call은 120이며 실제 값은 run manifest에 기록한다. 대형 pair batch는
reference/generated 본문을 ID table로 한 번씩만 전달하여 pair마다 본문이 반복되지 않도록 한다.

## 5. Matching

Judge는 reference/generated 위험 항목 쌍의 semantic_match를 0~4로 판정한다.
semantic_match >= 3인 pair만 match 후보가 된다.

최종 대응은 Python scipy의 maximum-weight bipartite matching으로 1:1 확정한다.
semantic match가 최우선이며 사고유형, 감소대책, 법규 점수는 동률 해소를 위한
하위 가중치로 사용한다. 사용한 scipy 버전과 평가 코드 hash는 manifest에 기록한다.

## 6. 대표 KPI

1. Reference Risk Coverage
   - matched reference risks / all reference risks
   - 높을수록 좋음

2. Unsupported Risk Rate
   - unsupported generated risks / all generated risks
   - 낮을수록 좋음

3. Accident Type Correctness
   - matched pairs 중 사고유형 적합 점수 2인 비율
   - 높을수록 좋음

4. Mitigation Appropriateness
   - matched pairs 중 감소대책 적합 점수 2인 비율
   - 높을수록 좋음

5. Mitigation Specificity
   - matched pairs 중 감소대책 구체성 점수 2인 비율
   - 높을수록 좋음

6. Legal Basis Presence
   - matched generated risks 중 법규 근거가 제공된 비율
   - 존재 여부와 관련성을 분리하여 측정

7. Legal Basis Relevance
   - 법규가 실제로 제공된 matched generated risks 중 관련성 점수 2인 비율
   - 높을수록 좋음

8. Critical Safety Error Rate
   - critical safety error generated risks / all generated risks
   - 낮을수록 좋음

9. Schema Compliance
   - deterministic 필수 구조를 만족한 generated risks / all generated risks

10. Deterministic Consistency
    - 빈도/강도 범위, 초기 산술, 개선 후 산술, 개선 후 위험 비증가 각각의 통과율

모든 비율형 지표는 numerator, denominator, rate를 저장한다.
aggregate report에는 Wilson 95% confidence interval과 case-level macro 평균/표준편차도 저장한다.

## 7. Judge calibration gate

공식 full run 전에 Judge model, reasoning effort, chunk 설정, prompt, rubric,
평가 코드와 dataset identity를 pilot manifest에 동결하고 human validation으로 검증한다.

기본 계획:
- 50-case pilot 결과 활용
- human_pairs.csv: 최대 150 reference-generated pair
- human_generated.csv: 최대 150 generated risk
- 안전전문가 2인 독립평가 + disagreement adjudication
- Judge 예측은 두 인간 라벨링 파일에 노출하지 않음
- pair sampling은 Judge 점수가 아닌 deterministic accident-label-overlap proxy 활용
- generated sampling은 고정 seed 기반 deterministic shuffle
- 동일 frozen Judge를 3회 반복 실행해 차원별 repeatability 측정

pair calibration 차원:
- semantic_match
- accident_type_correctness
- mitigation_appropriateness
- mitigation_specificity
- legal_basis_relevance (generated legal basis가 있는 경우만)

generated-only calibration 차원:
- unsupported_claim
- critical_safety_error

초기 gate:
- Semantic Human-Judge binary agreement >= 0.90
- Semantic Cohen's kappa >= 0.70
- 나머지 pair 차원 Human-Judge binary agreement >= 0.85
- 나머지 pair 차원 Cohen's kappa >= 0.60
- generated boolean 차원 Human-Judge agreement >= 0.90
- Overall repeatability >= 0.95
- Minimum per-dimension repeatability >= 0.95
- Structured-output completion >= 0.99
- Human label completion = 1.00
- pair 차원별 유효 sample >= 30
- generated 차원별 유효 sample >= 30

boolean safety event는 prevalence가 매우 낮을 경우 kappa가 불안정해질 수 있으므로
unsupported/critical 판정의 kappa는 보고하되 hard gate에는 agreement를 사용한다.

calibration gate_result.json에는 pilot run manifest SHA-256과 frozen method identity를 저장한다.
method identity에는 dataset SHA-256, evaluation source-tree SHA-256, prompt/rubric/config/lock
해시, Judge model/reasoning/max_pairs_per_call이 포함된다. repeatability와 full run은
이 identity가 현재 설정과 정확히 일치하지 않으면 실행을 차단한다.

gate가 없거나 통과하지 못한 경우 full 425-case run은 기본적으로 실행 자체를 차단한다.
개발용 명시적 override는 제공하지만 official candidate로 사용할 수 없다.

## 8. 재현성 및 감사추적

모든 run은 생성 시 immutable manifest를 기록한다.

- scenario JSONL SHA-256
- dataset provenance 및 원본 workbook SHA-256
- evaluation spec/rubric/prompt/uv.lock SHA-256
- evaluation source-tree SHA-256
- 평가 harness git HEAD 및 dirty 상태
- Python/platform/package versions
- SUT endpoint 및 risk-assessment format/model mode/reasoning style
- Judge model/reasoning effort/max_pairs_per_call
- calibration gate file SHA-256 및 pass 여부
- production Core/Agents git HEAD
- production Core/Agents 전체 repo dirty 상태 (감사용)
- production Core/Agents 위험성평가 실행 관련 relevant source-tree fingerprint
- calibration frozen method identity 및 current-method match 여부
- case별 production session/run id
- raw SUT 최종 content와 durable SSE event
- raw structured Judge 결과와 response metadata/usage
- SUT create-run retry 및 SSE reconnect log
- SUT latency mean/median/p95와 retry rate
- Judge call/input/output/total/reasoning/cached token aggregate
- deterministic check 결과
- matching 결과
- case별/aggregate metrics

API key, token, password는 artifact에 저장하지 않는다.

SUT create-run의 retry는 동일 clientRequestId를 재사용하여 서버 dedupe 계약을 유지한다.
SSE stream이 transport 오류나 비정상 종료로 끊기면 마지막 durable event sequence 이후부터
재연결하고 sequence/fingerprint 기준으로 중복 event를 제거한다. retry 횟수와 사유는 case artifact에 기록한다.

production Core/Agents는 전체 repository 상태를 기록하되 official stability 판정에는
위험성평가 실행에 관련된 source scope만 hash한다. Core는 agents/chat/auth/users/common과
부트스트랩/패키지 설정, Agents는 src/mastra 실행 소스와 패키지 설정이 해당된다.
run 시작과 종료의 relevant source fingerprint가 달라지면 official candidate로 인정하지 않는다.
resume 시에도 기존 manifest와 현재 relevant SUT fingerprint 또는 evaluation method identity가
다르면 재개를 차단한다.

## 9. Checkpoint 및 resume

각 case는 다음 checkpoint를 atomic rename 방식으로 독립 저장한다.

1. sut.json
2. parsed.json
3. judge.json
4. result.json
5. error.json - 실패 시

중단 후 같은 run id로 재개하면 완료된 가장 깊은 checkpoint부터 이어간다.
예를 들어 Judge 단계에서 실패하면 이미 완료된 production SUT 호출은 반복하지 않는다.
batch 실행 중 progress bar는 processed/total, percentage, 현재 case, stage, 누적 retry, elapsed, ETA를 표시한다.

## 10. 실행 단계

1. Dataset import/validation
2. Scenario build 및 leakage 검사
3. Offline unit/integration test
4. doctor/preflight
5. 10-case smoke
6. 50-case pilot
7. Human calibration + Judge repeatability
8. Calibration gate freeze
9. Full 425-scenario official candidate run
10. JSON/CSV aggregate report 생성
11. 시험기관이 요구하는 최종 공식 보고서 양식으로 frozen artifact 패키징

## 11. Official candidate validity

summary의 official_candidate_valid는 다음 조건을 모두 만족할 때만 true다.

- run mode = full
- 선택된 425 case 전부 완료
- failed case = 0
- calibration gate = PASS
- full run의 evaluation/Judge method identity가 calibration frozen identity와 동일
- run 시작/종료 production SUT relevant source fingerprint 동일
- calibration source evaluator와 full evaluator 모두 git commit 존재 + clean working tree

## 12. 비고

본 문서는 KOLAS 인정 또는 특정 공인시험기관의 승인 자체를 주장하지 않는다.
최종 시험항목, 합격기준, 보고서 양식은 의뢰할 KOLAS 공인시험기관과 협의 후 freeze한다.

현재 프로젝트는 감사 가능한 JSON/CSV를 canonical 결과로 저장한다.
full run 완료 후 모든 canonical artifact의 path/size/SHA-256을 `run_seal.json`에 기록하고
정렬된 artifact 목록으로 root SHA-256을 계산한다. `verify`는 누락, 변조, 예상 외 추가 파일과
root digest 불일치를 검출한다. 재봉인 시 이전 seal의 SHA-256을 기록하여 이력을 남긴다.

시험기관이 요구하는 XLSX 등 최종 제출 양식은 canonical frozen artifact에서
별도 생성한다.
