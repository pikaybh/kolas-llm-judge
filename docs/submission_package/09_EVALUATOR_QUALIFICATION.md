# Evaluator / LLM Judge 적격성 및 반복안정성 보고서

- 문서 ID: `KOLAS-DOC-009`
- 버전: `0.1-review`
- 상태: `REVIEW`
- 기준일: `2026-10-11`
- Qualification: `ajqg-v1`
- Gate: `ajqg-gate-v1`
- Control suite: `ajqg-controls-v1`
- Judge: `gpt-5.6-sol`, reasoning `medium`

> 결론: frozen AJQG v1의 완전한 qualification 기록 9건을 재감사한 결과 9/9 모두 gate PASS였다. 8건은 반복결정 376/376 일치였고, 1건은 375/376(99.734%)이었다. 해당 1건에서도 모든 gate threshold를 충족했다. 시험 당일에는 동일 frozen suite로 AJQG를 다시 실행하고 PASS한 경우에만 SUT 본시험을 시작한다.

## 1. 목적

AJQG는 LLM Judge를 사람과 동일하다고 증명하는 절차가 아니다. 다음을 시험 직전 자동 확인하는 **측정도구 적격성 gate**다.

- structured output completion
- positive semantic match control
- negative semantic match control
- accident compatibility control
- mitigation control
- legal relevance control
- critical-safety control
- robustness control
- repeated Boolean decision stability

Expected Boolean은 control 생성 규칙상 사전에 결정되어 있으며, 별도 인간 전문가 라벨을 사후 생성하지 않는다.

## 2. Control suite

Seed: `configs/ajqg_seed_v1.yaml`

- suite version: `ajqg-seed-v1`
- 대표 건설안전 hazard seed: 8개
- SHA-256: `f0f11537d77555e55fe5ae143fa92e92ddc631da1d7a1711fe2f070ad38b8586`

Generated control suite:

- version: `ajqg-controls-v1`
- controls: `104`
- SHA-256: `e0a34a8179d407979fc14f6ae1987a3fbf95f76ae8b0e29181fdc1efa8e3e437`

| Family | Control 수 | Accuracy 판정 Boolean 수 |
|---|---:|---:|
| match_identity | 8 | 24 |
| match_negative | 8 | 24 |
| accident | 16 | 16 |
| mitigation | 32 | 128 |
| legal | 16 | 16 |
| critical_safety | 16 | 16 |
| robustness | 8 | 24 |
| **합계** | **104** | **248** |

두 repeat의 전체 structured response를 직접 비교할 때는 Match 120 + Quality 240 + Safety 16 = **376 Boolean decisions**가 비교 대상이다.

## 3. Gate threshold

`configs/ajqg_gate_v1.yaml` SHA-256:

`2ee9934e921fa82b10697d6cf9ffca6e72f151a49159ac3aff7a8b7d17421a6b`

| Metric | Minimum |
|---|---:|
| structured completion | 99.5% |
| match identity accuracy | 100% |
| match negative accuracy | 98% |
| accident accuracy | 98% |
| mitigation accuracy | 95% |
| legal accuracy | 95% |
| critical safety accuracy | 98% |
| robustness accuracy | 98% |
| repeated decision stability | 98% |
| required control families | all present |

하나라도 gate를 통과하지 못하면 official SUT run을 시작하지 않는다.

## 4. Canonical hardening qualification evidence

선정 evidence:

`runs/_qualification/20260914-kolas-v1-hardening/`

### 4.1 Artifact hashes

| Artifact | SHA-256 |
|---|---|
| `summary.json` | `8ecffc8120381fb612b20b318ce916889a71da2005fde9b643515e6b3ac99309` |
| `control_results.csv` | `f362861e34544dce100d600218ce23f0953e4cb87aa915f980a830e53d3fbf58` |

### 4.2 결과

- control count: 104
- repeats: 2
- Judge: `gpt-5.6-sol`
- reasoning: `medium`
- structured completion: 6/6 = 100%
- match identity: 24/24 = 100%
- match negative: 24/24 = 100%
- accident: 16/16 = 100%
- mitigation: 128/128 = 100%
- legal: 16/16 = 100%
- critical safety: 16/16 = 100%
- robustness: 24/24 = 100%
- repeated decisions: 376/376 = 100%
- gate: **PASS**

OpenAI response metadata의 `response_model`도 6개 call 모두 `gpt-5.6-sol`로 기록되어 있다.

## 5. Historical qualification repeatability audit

완전한 metric structure와 2-repeat 결과가 남아 있는 qualification 기록 9건을 재감사했다.

| 항목 | 결과 |
|---|---:|
| 완전 qualification run | 9 |
| gate PASS | 9/9 |
| structured completion 최저 | 100% |
| semantic positive 최저 | 100% |
| semantic negative 최저 | 100% |
| accident 최저 | 100% |
| legal 최저 | 100% |
| critical safety 최저 | 100% |
| robustness 최저 | 100% |
| mitigation accuracy 범위 | 99.21875% ~ 100% |
| repeated decision stability 범위 | 99.73404% ~ 100% |

따라서 관찰된 provider-side Boolean 변동은 frozen AJQG gate 범위 안에 있었다.

## 6. Boundary / disagreement 사례

완전 qualification 9건 중 한 run에서만 first-repeat expected decision 1개가 다르게 판정되었다.

Evidence:

`runs/20260909T025259Z-official-live-ca5f3e25/qualification/`

Hashes:

- `summary.json`: `958fd53cba792d5e147697cb4b997fa71dbb2219caf49d318b52bb2951fb1a8b`
- `control_results.csv`: `2e60e30232b088628fc954d4bf23421bc68527b83186223e19ccea398f24c304`

Mismatch:

```text
control_id: electric:mitigation-unsafe
family: mitigation
dimension: mitigation_specific
expected: false
actual: true
mutation: reverse safe-control principle
```

이 run의 mitigation accuracy는 127/128 = 99.21875%로 gate 95%를 상회했다. 두 repeat 전체 Boolean stability는 375/376 = 99.73404%로 gate 98%를 상회했다.

`mitigation_specific`은 unsafe 여부와 별개의 Boolean이다. 해당 control에서 핵심 safety Boolean인 unsafe/critical 판정까지 실패했다는 증거는 없다. 따라서 이 사례는 Judge가 항상 문자 그대로 동일한 결과를 보장하지 않는다는 점과, 이를 흡수하기 위해 frozen gate와 repeat stability 조건이 필요한 이유를 보여주는 boundary evidence로 사용한다.

## 7. Accuracy라는 표현의 범위

본 AJQG의 family별 `accuracy`는 **construction-defined expected Boolean control에 대한 일치율**이다.

따라서 다음처럼 표현한다.

- 적절: “AJQG constructed-control accuracy”
- 부적절: “인간 전문가 정답 대비 Judge 정확도 100%”

별도의 Human–LLM blinded calibration 기능은 저장소에 구현되어 있으나 official mandatory gate가 아니며, 본 qualification 보고서의 9-run 통계와 섞지 않는다.

## 8. Requalification 규칙

다음 변경이 있으면 기존 PASS를 승계하지 않는다.

- model identifier 또는 reasoning effort 변경
- prompt/rubric 변경
- control seed/generation/gate 변경
- output schema 변경
- match/aggregation rule 변경
- evaluator source aggregate hash 변경
- OpenAI SDK/runtime의 판정 semantics에 영향을 줄 수 있는 변경

또한 **공식 시험 시작 직전** frozen configuration으로 AJQG를 다시 실행한다.

## 9. 2026-10-11 현재 재실행 상태

2026-10-11 현 상태에서 동일 `qualify-judge --repeats 2 --require-pass` 실행을 시도했으나 `.env`의 OpenAI credential이 현재 인증되지 않아 API 401에서 중단됐다.

이 실행은 Judge가 control을 판정하기 전에 API 인증 단계에서 실패했으므로 AJQG FAIL로 계산하지 않는다. 시험기관용 credential provisioning 단계에서 유효 key를 설정한 뒤 AJQG를 다시 실행해야 한다.

## 10. 제출 시 권장 증적

시험기관에 다음을 함께 제시한다.

1. `configs/official_runtime_v1.yaml`
2. `configs/ajqg_seed_v1.yaml`
3. `configs/ajqg_gate_v1.yaml`
4. `prompts/judge_binary_v1.md`
5. `configs/rubric_binary_v1.yaml`
6. canonical qualification `summary.json`
7. canonical qualification `control_results.csv`
8. 시험 당일 새로 생성되는 AJQG `summary.json` / `control_results.csv`
9. 각 파일 SHA-256 및 run manifest

시험 당일 AJQG 결과가 gate FAIL이면 SUT 본시험을 공식 유효 run으로 진행하지 않는다.
