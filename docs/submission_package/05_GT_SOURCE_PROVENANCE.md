# Ground Truth 출처 Provenance 및 Traceability 명세

- 문서 ID: `KOLAS-DOC-005`
- 버전: `0.2-draft`
- 상태: `REVIEW`
- 기준일: `2026-10-11`
- Dataset ID: `KOLAS_RA_GT`
- Dataset version: `1.0.0`
- Provenance schema: `kolas-gt-provenance-v1`
- 관련 GT 명세: `04_GT_SPECIFICATION.md`
- GT 검증 상태: 연구실 구성원 검토를 거쳐 이미 검증 완료

> 결론: `KOLAS_RA_GT v1.0.0`은 **연구실 구성원들의 검토를 거쳐 이미 검증된 데이터셋**이다. 별도로, 현재 파일 lineage는 843/843 추적 가능하지만 각 위험요인의 원작성 safety-source provenance는 구조화되어 있지 않다. 본 문서는 GT의 유효성을 다시 검증하기 위한 문서가 아니라 출처 추적성과 무결성을 정리하기 위한 문서다.

## 1. Provenance의 세 층

본 제출에서는 provenance를 다음 세 층으로 분리한다.

### Layer A — Artifact/File lineage

“이 reference가 어느 legacy dataset row에서 현재 evaluator의 어느 reference로 변환되었는가?”

현재 상태: **843/843 추적 가능**

### Layer B — Safety-content source provenance

“그 legacy row의 위험요인이 어떤 법령, 공공기관 가이드, 기술기준, 논문, 현장기록 등 안전지식 근거에서 작성되었는가?”

현재 상태: **reference-level 원작성 source 정보가 별도 구조화되어 있지 않음**

### Layer C — Existing laboratory validation

GT 자체는 연구실 구성원들의 검토를 거쳐 이미 검증된 데이터로 사용한다. 본 제출 준비에서는 동일 GT를 대상으로 별도의 신규 전문가 검증 절차를 다시 수행하지 않는다.

파일 lineage와 원작성 source provenance는 이 기존 GT 검증 사실과 별개의 추적성 문제로 관리한다.

## 2. 확인된 legacy lineage

Tracked `data/raw/PROVENANCE.md`에 따르면:

1. legacy KOLAS evaluation package에 XLSX workbook 형태로 dataset이 존재했다.
2. workbook에는 843 data rows, 11 columns가 있었다.
3. pandas로 workbook을 읽어 UTF-8 CSV로 표현한 뒤 bzip2로 압축했다.
4. 해당 processing representation을 현재 evaluator가 사용한다.

식별값:

| Artifact | SHA-256 | 현재 bytes |
|---|---|---|
| Original XLSX workbook | `d12c7d683518b680615e2311f49059ed3f5c439cf6c706afb671b6c7bcafdd4a` | 현재 서버에서 미확보 |
| Processing CSV.bz2 | `b76c9efa718a0429f587b311d9e6e1d2107bf13101b0f91bc02a69e695ad142a` | local 존재 |
| Scenario JSONL | `2cdc1e8b9e05766d29790965bcf09c4015662daf8c70571209bccb4a15ee419c` | local 존재 |

2026-10-11 server-wide non-dependency XLS/XLSX audit에서 보존된 workbook hash와 일치하는 XLSX는 발견되지 않았다.

## 3. 현재 source provenance가 없는 이유

Processing source의 11개 column에는 다음과 같은 provenance field가 없다.

- source document ID
- 출처기관
- 문헌/가이드 제목
- page/section/article locator
- URL
- source file hash
- 작성자/검토자
- 생성 근거

`관련근거(법규)` field가 805행에 존재하지만 이것은 각 reference의 **legal basis label**일 뿐, 해당 hazard row가 실제로 그 법령에서 추출·작성되었다는 provenance 증거와 동일하지 않다.

따라서 법규 문자열이 존재한다는 이유만으로 Layer B provenance를 “확보”로 계산하지 않는다.

## 4. Reference-level provenance ledger

파일:

`data/cases/gt_provenance_register_v1.csv`

SHA-256:

`00b52d389e2afc170c4114ac0308075199beb94d33c725a1beed6b370a679f1c`

Ledger는 843개의 모든 reference에 한 행씩 존재하며 raw hazard text 대신 `reference_hazard_sha256`를 기록한다.

### 4.1 Ledger fields

| Field | 의미 |
|---|---|
| `dataset_id` | `KOLAS_RA_GT` |
| `dataset_version` | `1.0.0` |
| `case_id` | scenario permanent ID |
| `reference_id` | reference permanent ID |
| `source_row` | legacy source physical row |
| `reference_hazard_sha256` | frozen hazard text digest |
| `lineage_origin` | legacy origin classification |
| `provenance_status` | 현재 증적 상태 |
| `source_type` | authoritative source type |
| `source_id` | 내부 source registry ID |
| `locator` | page/section/clause/URL 등 locator |
| `source_sha256` | 보관 source file의 hash |
| `license_status` / `external_sharing` | 라이선스 및 외부 제공 범위 |
| `expert_validation_status` | Phase 4 validation 상태 |

### 4.2 현재 843개 row의 값

- `lineage_origin = legacy_kolas_v7_73_workbook`
- `provenance_status = unresolved`
- `source_type = LEGACY_WORKBOOK_ONLY`
- `source_id = blank`
- `locator = blank`
- `expert_validation_status = pending`

이는 “출처가 없다”를 숨기는 placeholder가 아니라 **현재 확인 가능한 사실 자체**다.

## 5. Provenance manifest

파일:

`data/cases/gt_provenance_audit_manifest_v1.json`

SHA-256:

`ec5bd4f9fded546ac4f2671da5e610688e674193135c9fc1c3b9ef7ac9c3727c`

Current coverage:

| Coverage item | Count | Rate |
|---|---:|---:|
| Reference rows | 843 | 100% |
| Row lineage covered | 843 | 100% |
| Original-source provenance structured | 0 | 별도 구조화 없음 |
| Unresolved source | 843 | 100% |
| GT validation | 연구실 구성원 검토 완료 | 완료 |

Manifest status:

`INCOMPLETE_LEGACY_PROVENANCE`

Schema: `configs/gt_provenance_schema_v1.yaml` (`58d9ad6b9566b17bc114786b037e0efcd901ba9de316a5241f72fd4c06c03fe2`)

Blank register template: `docs/submission_package/templates/GT_PROVENANCE_REGISTER_TEMPLATE.csv`

## 6. Source type taxonomy

향후 provenance를 보강할 때 `configs/gt_provenance_schema_v1.yaml`의 controlled vocabulary를 사용한다.

| `source_type` | 의미 |
|---|---|
| `LAW_REGULATION` | 법률·시행령·시행규칙·고시 등 법적 근거 |
| `KOSHA_GUIDE` | KOSHA Guide/기술지침 |
| `PUBLIC_AGENCY_GUIDE` | 정부·공공기관 발간 안전자료 |
| `SITE_RISK_ASSESSMENT` | 식별 가능한 현장 위험성평가/작업계획 |
| `ACCIDENT_CASE` | 공공기관 재해사례/사고조사 자료 |
| `RESEARCH_LITERATURE` | 논문·연구보고서 등 학술근거 |
| `MANUFACTURER_MANUAL` | 제조사 공식 장비/안전 매뉴얼 |
| `EXPERT_AUTHORED` | 작성자 증적과 승인기록이 있는 전문가 작성 기준 |
| `LEGACY_WORKBOOK_ONLY` | file lineage만 확인되고 authoritative source는 미해결 |
| `OTHER` | 별도 설명이 필요한 기타 출처 |

현재 843개 reference는 모두 `LEGACY_WORKBOOK_ONLY`에서 시작한다. 작성자 증거 없이 `EXPERT_AUTHORED`로 소급 분류하지 않는다.

## 7. Source document registry 요구사항

향후 source document를 회수하거나 새로 채택하면 source별로 최소 다음 metadata를 기록한다.

- `source_id`
- source type
- 문서 제목
- 발행기관/저자
- 문서 version/revision
- 발행일 또는 확인일
- 원본 URL 또는 archive location
- local archival file SHA-256 (허용 시)
- license/access classification
- source recovery date
- recovery/operator record

## 8. Reference-to-source locator 요구사항

각 reference와 source를 연결할 때 최소 다음 locator 중 해당되는 것을 기록한다.

- page number
- section/chapter
- article/clause
- table/figure ID
- official URL + anchor/query
- document record ID
- field/site record ID

`locator`는 제3자가 같은 source를 열어 동일 근거를 찾을 수 있을 정도로 구체적이어야 한다.

필요한 경우 짧은 evidence excerpt 또는 요약을 별도 필드/첨부로 둘 수 있으나, 저작권이 있는 source의 장문 원문을 provenance ledger에 복제하지 않는다.

## 9. Source 적용 판정 규칙

source를 찾았다고 해서 즉시 GT 근거로 승인하지 않는다.

Reference별로 다음을 확인한다.

1. 해당 source가 같은 작업/설비/물질 context에 적용되는가?
2. source가 동일 hazard mechanism을 직접 또는 합리적으로 지지하는가?
3. 단순히 같은 사고유형만 언급하는 것은 아닌가?
4. source version/date가 시험대상 시점에 유효한가?
5. locator가 실제 근거 내용으로 연결되는가?
6. source가 GT 자체에서 파생된 circular source는 아닌가?

특히 현재 SEEXR RA 검색 DB는 legacy GT와 데이터 계보가 겹칠 가능성을 배제할 증거가 없으므로, **원출처 입증 없이 RA DB 내용을 GT provenance로 역채택하지 않는다.**

## 10. Source가 회수되지 않는 reference의 처리

Legacy origin을 끝내 복원할 수 없는 reference는 두 가지 중 하나로 처리한다.

### A. 전문가가 현재 GT를 독립적으로 승인

- 기존 검증된 GT 내용은 그대로 유지
- 원작성 source가 필요할 경우 별도로 source provenance만 보강
- GT 내용을 변경해야 하는 경우에만 별도 변경통제 절차 적용

이 경우 legacy “원출처”를 복원했다고 표현하지 않는다. 대신 `legacy origin unresolved; independently expert-validated`로 구분한다.

### B. 전문가가 부적합/불명확 판정

- 기존 `v1.0.0` row는 audit lineage를 위해 보존
- accreditation용 다음 GT version에서 수정/제외 후보 처리
- old→new ID mapping과 변경사유 기록
- 변경된 dataset으로 필요한 시험을 다시 수행

## 11. Original workbook recovery 절차

현재 원본 XLSX bytes는 미확보다. 복구 시 다음 순서로 확인한다.

1. legacy KOLAS delivery package, email attachment, cloud/archive, 외장 backup 등에서 후보 파일 회수
2. SHA-256 계산
3. `d12c7d683518b680615e2311f49059ed3f5c439cf6c706afb671b6c7bcafdd4a`와 일치 여부 확인
4. 일치하면 read-only evidence storage에 보존
5. workbook → processing representation 재생성 가능성을 별도 확인
6. 원본에 숨은 source metadata/sheet/comment/link가 있는지 감사

hash가 다르면 “비슷한 workbook”을 원본이라고 선언하지 않는다.

## 12. License / 외부 제공 상태

현재 확인 가능한 상태:

- raw GT/processing source는 repository `.gitignore`에서 proprietary/raw evaluation data로 취급된다.
- 원본 workbook의 법적 배포권/라이선스 metadata는 현재 증적에서 확인되지 않았다.
- 개별 hazard의 원문 source document가 없으므로 그 source들의 license/access도 현재 판정할 수 없다.

따라서 시험기관 전달 시:

- raw GT는 승인된 secure package 또는 controlled access로 제공
- source document는 각 문서별 외부 제공 가능 여부를 확인
- 공개 배포가 불가한 source는 hash + locator + 기관 열람 방식으로 증적하는 방안을 협의

## 13. Integrity 및 변경통제

Provenance ledger는 raw hazard text를 담지 않지만 `reference_hazard_sha256`를 통해 frozen scenario content와 연결된다.

`tests/test_gt_provenance.py`는 다음을 검증한다.

- ledger row count = 843
- reference ID set 완전 일치
- source row 완전 일치
- hazard SHA-256 완전 일치
- raw hazard text 미포함
- 현재 unresolved 상태가 명시적임
- manifest가 raw/scenario/ledger 실제 hash와 일치함

향후 provenance row를 보강할 때 GT hazard 내용이 변경되지 않았다면 `reference_hazard_sha256`는 유지되어야 한다.

## 14. GT 검증 상태 기록

`KOLAS_RA_GT v1.0.0`은 연구실 구성원들의 검토를 거쳐 이미 검증된 데이터셋이다.

본 제출 준비에서는 별도의 신규 전문가 검증, 신규 합의도 통계 산출, 추가 reviewer 모집을 요구하지 않는다. 기존 검증의 세부 인원수·절차·통계값은 확인된 기록이 없는 한 임의로 작성하지 않는다.

## 15. 현재 Gap과 완료 기준

Phase 3가 최종 완료되려면 원칙적으로 임의 reference를 선택했을 때 safety-content source까지 추적 가능해야 한다. 현재는 그렇지 않다.

따라서 Phase 3 상태는 `REVIEW / INCOMPLETE`다.

남은 Critical 작업:

- [ ] original source provenance 복구 또는 대체 근거 수집
- [ ] 843 reference에 source document + locator 연결
- [ ] source license/access classification
- [x] GT는 연구실 구성원 검토를 거쳐 검증 완료된 데이터로 사용
- [ ] duplicate/near-duplicate candidate adjudication
- [ ] 최종 accreditation GT freeze 및 integrity seal

## 16. HWP 반영 지시

붙임 3의 “GT 출처 및 검증” 절에는 다음을 명확히 분리한다.

1. **확인된 계보:** legacy workbook hash → processing source → scenario/reference
2. **미확인 계보:** 각 hazard의 원 안전자료 출처
3. **보완 절차:** 필요 시 source provenance 보강
4. **정량 coverage:** 843/843 row lineage; GT 자체는 연구실 검증 완료

출처가 없는 legacy dataset을 마치 공공기관 자료로부터 직접 구축한 것처럼 서술하지 않는다.
