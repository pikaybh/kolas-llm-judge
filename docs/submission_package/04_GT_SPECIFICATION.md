# Ground Truth 데이터셋 명세 및 Freeze 규칙

- 문서 ID: `KOLAS-DOC-004`
- 버전: `0.2-draft`
- 상태: `REVIEW`
- 기준일: `2026-10-11`
- Dataset ID: `KOLAS_RA_GT`
- Dataset version: `1.0.0`
- Schema version: `kolas-ra-dataset-v1`
- Evidence IDs: `EV-GT-001` ~ `EV-GT-006`
- 관련 시험방법: `01_TEST_METHOD.md`
- 관련 provenance: `05_GT_SOURCE_PROVENANCE.md`

> 이 문서는 현재 `KOLAS_RA_GT v1.0.0`의 **내용·구조·변환 규칙·식별자·무결성**을 명세한다. 이 문서만으로 843개 위험요인의 안전지식적 정당성이 입증되는 것은 아니다. 개별 위험요인의 근거 출처와 전문가 검증은 별도 provenance/validation 증적으로 관리한다.

## 1. GT 역할과 적용 범위

`KOLAS_RA_GT v1.0.0`은 SEEXR 위험성평가 AI의 **Hazard Identification** 성능을 시험하기 위한 reference dataset이다.

현재 KOLAS-facing primary metric에서 직접 reference로 사용하는 핵심 필드는 `hazard`이며, semantic match는 `same_hazard_mechanism AND context_compatible` 규칙으로 판정한다.

GT의 사고분류, 위험도, 감소대책, 법규 필드는 legacy dataset의 부가 reference 정보로 보존되지만, 현재 primary Hazard Semantic Identification Recall의 정답 판정식을 임의로 확장하지 않는다.

## 2. Canonical artifact hierarchy

현재 GT 계보는 다음 4단계로 구분한다.

| 계층 | Artifact | 역할 | 현재 상태 |
|---|---|---|---|
| Legacy origin | 원본 XLSX workbook | legacy dataset 원본 | bytes는 현재 repository/server에서 미확보, hash만 보존 |
| Processing source | `data/raw/kolas_v7_73_test.csv.bz2` | evaluator가 실제 읽는 843행 전송 표현 | local 존재, Git ignored |
| Evaluation canonical | `data/cases/scenarios_v1.jsonl` | 425 scenario / 843 reference의 실제 시험 canonical | local 존재, Git ignored |
| Metadata | `data/cases/dataset_manifest.json` | dataset identity·수량·hash | Git tracked |

### 2.1 고정 hash

| Artifact | SHA-256 |
|---|---|
| Original XLSX workbook | `d12c7d683518b680615e2311f49059ed3f5c439cf6c706afb671b6c7bcafdd4a` |
| Processing source CSV.bz2 | `b76c9efa718a0429f587b311d9e6e1d2107bf13101b0f91bc02a69e695ad142a` |
| Scenario JSONL | `2cdc1e8b9e05766d29790965bcf09c4015662daf8c70571209bccb4a15ee419c` |
| Dataset manifest | `e7679fabc39f6c6abb7eb53fdc72a9374deb8b0e64add9cdff4e89ec1cfddc2a` |
| `data/raw/PROVENANCE.md` | `571f5cf43ce7e309ac93cf1f4312879eff5f966c7dc457db601304939316367a` |

원본 XLSX bytes는 2026-10-11 서버 감사에서 발견되지 않았다. 따라서 원본 XLSX의 hash는 **보존된 lineage identifier**이지 현재 로컬 파일에 대해 재계산한 값이 아니다.

## 3. Raw source schema

Processing source는 843행 × 11열이며 정확한 column name은 다음과 같다.

1. `공정`
2. `세부공정`
3. `설비`
4. `물질`
5. `유해위험요인`
6. `사고분류`
7. `위험 가능성`
8. `위험 중대성`
9. `위험성`
10. `감소대책`
11. `관련근거(법규)`

필수 validation:

- dataset이 비어 있지 않아야 한다.
- `공정`은 null이 없어야 한다.
- `유해위험요인`은 null이 없어야 한다.
- 11개 required column이 모두 존재해야 한다.

## 4. Scenario / Reference schema

### 4.1 `EvaluationScenario`

| Field | Type | 생성 규칙 |
|---|---|---|
| `case_id` | string | cleaned `공정 + 세부공정` canonical JSON의 SHA-256 앞 12자리, `case-` prefix |
| `source_rows` | int[] | scenario에 포함된 원본 physical row number 목록 |
| `input` | ScenarioInput | SUT에 전달 가능한 작업 맥락 |
| `references` | ReferenceRisk[] | SUT에 숨겨지는 reference GT |

### 4.2 `ScenarioInput`

| Field | Source | 처리 |
|---|---|---|
| `process` | 공정 | whitespace normalize/trim |
| `subprocess` | 세부공정 | normalize 후 blank이면 null |
| `equipment` | 설비 | scenario 내 nonblank 값 stable unique |
| `materials` | 물질 | scenario 내 nonblank 값 stable unique |

### 4.3 `ReferenceRisk`

| Field | Source | 처리 |
|---|---|---|
| `reference_id` | generated | `{case_id}-r{source_row}` |
| `source_row` | row position | header 포함 spreadsheet 기준 `2..844` |
| `hazard` | 유해위험요인 | whitespace normalize/trim |
| `accident_types` | 사고분류 | `;`로 split 후 trim |
| `likelihood` | 위험 가능성 | 괄호 안 첫 정수, 없으면 첫 정수 |
| `severity` | 위험 중대성 | 동일 |
| `risk_score` | 위험성 | 동일 |
| `mitigation` | 감소대책 | blank이면 null |
| `legal_basis` | 관련근거(법규) | blank이면 null |

## 5. 843행 → 425 scenario 변환 규칙

변환 구현은 `src/kolas_llm_judge/dataset.py`에 있다.

1. 원본 843행에 physical source row `2..844`를 순서대로 부여한다.
2. `공정`, `세부공정`에 `_clean()`을 적용한다.
3. cleaned `(공정, 세부공정)`을 key로 source order를 유지하여 grouping한다.
4. 각 source row를 **삭제·merge·deduplicate하지 않고 정확히 하나의 ReferenceRisk로 보존**한다.
5. 같은 scenario에서 설비/물질만 blank 제거 후 stable unique한다.
6. 425개의 scenario를 deterministic JSONL로 쓴다.

2026-10-11 재생성 검사에서 processing source로부터 새로 만든 JSONL은 기존 `scenarios_v1.jsonl`과 **byte-identical**했고 SHA-256도 동일했다.

## 6. Normalization 규칙

### 6.1 문자열 normalization

`_clean(value)`:

- missing/NaN → 빈 문자열
- 연속 whitespace → single space
- 양끝 whitespace 제거

현재 raw source에 대해 normalization으로 문자열 표현이 변하는 cell 수:

| Field | 변경 cell 수 |
|---|---:|
| 세부공정 | 5 |
| 유해위험요인 | 28 |
| 위험 가능성 | 163 |
| 위험 중대성 | 163 |
| 위험성 | 163 |
| 감소대책 | 244 |
| 관련근거(법규) | 1 |

cleaned 공정+세부공정 grouping key가 서로 다른 raw key를 우연히 합치는 collision은 **0건**이었다.

### 6.2 숫자 normalization

위험 가능성/중대성/위험성은 괄호 안 정수가 있으면 우선 사용하고, 아니면 첫 정수를 추출한다.

현재 dataset은:

- numeric triplet parse complete: **843/843**
- `likelihood × severity = risk_score`: **843/843 일치**
- likelihood values: `{1,2,3}`
- severity values: `{1,2,3}`
- risk score values: `{1,2,3,4,6,9}`

즉 legacy GT의 수치 risk labels는 **3×3 계열**이다. 현재 SUT official request의 `빈도강도법 5x4`와 같은 scale이라고 간주하면 안 된다. 현재 primary hazard-identification metric은 이 숫자들을 판정식에 사용하지 않는다.

## 7. Completeness audit

| Field | Nonblank | Blank |
|---|---:|---:|
| 공정 | 843 | 0 |
| 세부공정 | 784 | 59 |
| 설비 | 660 | 183 |
| 물질 | 142 | 701 |
| 유해위험요인 | 843 | 0 |
| 사고분류 | 843 | 0 |
| 위험 가능성 | 843 | 0 |
| 위험 중대성 | 843 | 0 |
| 위험성 | 843 | 0 |
| 감소대책 | 842 | 1 |
| 관련근거(법규) | 805 | 38 |

`유해위험요인`과 `공정`은 primary test에 필요한 범위에서 843/843 존재한다.

## 8. Scenario 분포

- unique process: `168`
- unique cleaned process/subprocess scenario: `425`
- references: `843`

Scenario별 reference 수 분포:

| refs/scenario | scenario count |
|---:|---:|
| 1 | 232 |
| 2 | 105 |
| 3 | 44 |
| 4 | 22 |
| 5 | 7 |
| 6 | 4 |
| 7 | 2 |
| 8 | 2 |
| 9 | 1 |
| 10 | 1 |
| 11 | 1 |
| 12 | 1 |
| 14 | 1 |
| 17 | 1 |
| 19 | 1 |

## 9. Reference leakage 방지

SUT input은 다음만 포함한다.

- process
- subprocess
- equipment
- materials

다음 reference-only 정보는 SUT request에 포함하지 않는다.

- hazard
- accident_types
- likelihood
- severity
- risk_score
- mitigation
- legal_basis

이 경계는 `tests/test_dataset.py`에서 검증한다.

## 10. ID 및 traceability 규칙

### 10.1 `source_row`

현재 source row는 original workbook/processing source의 physical data row를 나타내며 `2..844`가 정확히 한 번씩 존재한다.

### 10.2 `case_id`

case ID는 cleaned process/subprocess 내용에서 deterministic하게 만들어진다.

### 10.3 `reference_id`

reference ID는 `case_id + source_row`로 결정된다. 현재 843개 reference ID는 모두 unique하다.

### 10.4 영구 ID 정책

현재 알고리즘은 source row ordering에 의존한다. 따라서 `v1.0.0`을 freeze한 이후에는 source file을 reorder한 뒤 같은 알고리즘으로 ID를 재생성해서는 안 된다.

향후 GT를 변경할 때:

1. `v1.0.0` reference ID를 immutable legacy ID로 보존한다.
2. 내용 수정/merge/split/reorder가 있으면 dataset version을 올린다.
3. old reference ID → new reference ID mapping을 남긴다.
4. accreditation 결과에는 사용한 dataset version/hash를 함께 기록한다.

## 11. Duplicate / near-duplicate screening

완전 동일한 11-field raw row는 **0건**이다.

전역 cleaned hazard text 기준으로는 **24개 반복 문구 group / 55개 row / 최초 1건씩을 제외한 31개 extra row**가 존재한다. 이는 서로 다른 공정·세부공정 context까지 포함한 전역 screening 결과이며 자동 중복 제거 근거로 사용하지 않는다.

그러나 동일 scenario 안에서 hazard text만 기준으로 보면 전문가 검토가 필요한 candidate가 있다.

### 11.1 Exact cleaned hazard text pair — 4쌍

- source rows `351 / 596`
- source rows `428 / 481`
- source rows `266 / 735`
- source rows `704 / 761`

### 11.2 Punctuation/whitespace-equivalent pair — 1쌍

- source rows `258 / 765`

### 11.3 Near-duplicate candidate — 1쌍

- source rows `380 / 503`
- punctuation 제거 후 sequence similarity `0.949`

이 candidate들은 hazard text가 같거나 유사하더라도 설비·물질·사고분류·위험도·감소대책·법규 중 일부가 다르다. 따라서 Phase 3에서 임의 삭제/merge하지 않는다. Phase 4의 독립 전문가 검토에서 “동일 위험의 중복인지, 다른 context의 독립 reference인지”를 판정한다.

## 12. Provenance ledger 연결

`data/cases/gt_lineage_index_v1.csv`는 843개 reference의 `reference_id ↔ source_row ↔ case_id`를 고정한다. source rows `2..844`가 중복·누락 없이 정확히 한 번씩 존재하며 SHA-256은 `55c0aa75f8cc0ca542c1fb6755a06ed563f02b0150605a227f2539d907aefbd6`다.

`data/cases/gt_provenance_register_v1.csv`는 843개 reference 각각에 대해 다음을 추가로 고정한다.

- case ID
- reference ID
- source row
- hazard text의 SHA-256
- legacy lineage 상태
- source provenance 상태
- expert validation 상태

Raw hazard text 자체는 ledger에 복제하지 않는다.

Ledger SHA-256:

`00b52d389e2afc170c4114ac0308075199beb94d33c725a1beed6b370a679f1c`

Provenance audit manifest SHA-256:

`4a600e7dc88be21c5a0ade1cb0e3e1ef736448842a81a2292c1471b76160b7b4`

## 13. GT Freeze status

현재 데이터 내용 자체는 `KOLAS_RA_GT v1.0.0`으로 hash-fixed되어 있다. 그러나 KOLAS 제출 관점의 **accreditation-ready GT freeze는 아직 완료되지 않았다.**

이유:

- authoritative hazard-level source provenance: `0 / 843`
- independent expert validation: `0 / 843`
- duplicate candidate expert adjudication: 미완료
- 원본 XLSX bytes: 현재 로컬 미확보

따라서 현재 상태는:

`CONTENT-FROZEN / PROVENANCE-INCOMPLETE / EXPERT-VALIDATION-PENDING`

으로 표현한다.

## 14. Proprietary artifact packaging

`data/raw/*`와 `data/cases/*.jsonl`은 Git ignore 대상이다. 따라서 Git commit만으로 GT bytes를 복원할 수 없다.

최종 시험기관 전달 package에는 별도 승인된 방식으로 최소 다음을 포함하거나, 기관이 접근 가능한 secure storage reference를 제공해야 한다.

- exact processing source (`b76c9efa...`)
- exact scenarios JSONL (`2cdc1e8b...`)
- dataset manifest
- lineage index / provenance register / provenance audit manifest / provenance schema
- integrity manifest

원본 XLSX를 회수하면 hash `d12c7d68...` 일치 여부를 확인한 뒤 legacy-origin 증적으로 별도 봉인한다.

## 15. Phase 3 미해결 항목

| ID | 중요도 | 항목 | 상태 |
|---|---|---|---|
| `GAP-GT-001` | Critical | 843 reference별 authoritative source provenance | `0/843`, Phase 4/source recovery 필요 |
| `GAP-GT-002` | Critical | 독립 전문가 validation | `0/843`, Phase 4 필요 |
| `GAP-GT-003` | High | 원본 XLSX bytes | hash만 보존, local file 미확보 |
| `GAP-GT-004` | High | 6개 duplicate/near-duplicate candidate 판정 | expert adjudication 필요 |
| `GAP-GT-005` | Medium | source document license/access classification | source docs 자체 미확보로 판정 불가 |

## 16. HWP 반영 지시

최종 HWP 붙임 3에는 최소 다음을 포함한다.

- GT artifact 계보 및 hash 표
- 11-field raw schema / scenario-reference schema
- 843→425 변환 flow
- completeness 및 수치 일관성 표
- ID/versioning 규칙
- duplicate screening 결과와 처리 원칙
- `CONTENT-FROZEN`과 `accreditation-ready GT`를 구분한 상태 표
- provenance 및 전문가 검증 미완료 현황
