# 시험 데이터 독립성 및 Runtime Knowledge 중복 감사

- 문서 ID: `KOLAS-DOC-015`
- 버전: `0.1-review`
- 상태: `REVIEW`
- 기준일: `2026-10-13`
- Dataset: `KOLAS_RA_GT v1.0.0`
- Evidence IDs: `EV-GT-OVERLAP-20261013`, `EV-SUT-SOURCE-AUDIT-20261013`
- 관련 시험방법: `01_TEST_METHOD.md`
- 관련 SUT: `02_SYSTEM_UNDER_TEST.md`

## 1. 목적

한국인공지능검증원이 요청한 “학습 및 시험 데이터 간의 중복 활용 여부”를 확인하기 위해, 모델 fine-tuning/코드 하드코딩과 runtime retrieval knowledge를 구분하여 감사한다.

본 문서는 “중복 없음”을 가정하지 않는다. 확인된 범위와 확인할 수 없는 범위를 분리하여 기록한다.

## 2. SUT source 및 fine-tuning 경로 감사

2026-10-13 현재 다음 Git tracked code/config/docs를 대상으로 감사했다.

| Component | Git HEAD |
|---|---|
| Core | `2103544bac430dbc839150918496732311f2b739` |
| Agents | `aee7a80415a9fb2706894e92a8b084074719edd4` |
| RA API | `b400f87ffc483764e8a8857e12c188867425c2b2` |

감사 결과:

- SEEXR 자체 fine-tuning job/training-file 경로를 나타내는 tracked source 지표는 확인되지 않았다.
- 너무 짧아 우연 일치 가능성이 큰 문구를 제외하기 위해 길이 15자 이상 GT hazard 729건을 사용하여 exact normalized substring을 검색했다.
- Core, Agents, RA API tracked source에서 의미있는 exact GT hazard text occurrence는 각각 `0`건이었다.

Canonical evidence:

`data/submission/evidence/sut_gt_source_overlap_audit_20261013.json`

SHA-256:

`3bbf6d655a083281856529630ec5c1419a3def66a0728c196a4617b4947f9d56`

### 해석 범위

이 결과는 **SEEXR 자체 tracked source에서 GT를 fine-tuning dataset으로 사용하는 경로나 GT 위험문구를 대량 하드코딩한 증거를 찾지 못했다**는 의미다.

OpenAI 등 외부 provider의 base model 사전학습 데이터 구성은 SEEXR repository 감사만으로 확인할 수 없으므로 “외부 foundation model이 GT와 완전히 독립”이라고 주장하지 않는다.

## 3. RA retrieval DB와 시험 GT의 중복 감사

SEEXR quick-fast workflow는 `agent-api-ra`의 위험성평가 검색 DB를 runtime retrieval source로 사용한다. 따라서 이 DB는 모델 fine-tuning 여부와 별개로 시험 결과에 영향을 줄 수 있는 SUT 구성요소다.

2026-10-13 live local RA API의 ID `1..7000`을 조회하여 실제 존재하는 6,443개 row 전체를 수집하고 GT 843행과 비교했다.

정규화 규칙:

- leading/trailing whitespace 제거
- 연속 whitespace를 single space로 축약
- 그 외에는 exact string equality

결과:

| 비교 조건 | 일치 GT row | 비율 |
|---|---:|---:|
| hazard exact | 718 / 843 | 85.1720% |
| process + subprocess + hazard exact | 591 / 843 | 70.1068% |
| process + subprocess + equipment + material + hazard exact | 583 / 843 | 69.1578% |
| process + subprocess + equipment + material + hazard + accident + control + legal exact | 194 / 843 | 23.0130% |

Canonical evidence:

`data/submission/evidence/gt_ra_overlap_audit_20261013.json`

SHA-256:

`d622c3ec2e0cd5eec5dda0fdede80ec51d99083ef42a96ddb2c7858955308e87`

## 4. RA DB source-of-truth

현재 RA 검색 DB의 운영 source-of-truth는:

`/srv/green-server/agent-api-ra/sandbox/ra_db.xlsx`

SHA-256:

`48a6192906d33d9287057a761cafabdc41660adc781c9cf2ef0ac9a08e0fec8a`

관련 운영 절차:

`/srv/green-server/agent-api-ra/docs/DATABASE_UPDATE_PROTOCOL.md`

현재 데이터 흐름은 Excel → DB seed/upsert → embedding → hybrid retrieval이다. `scripts/seed.py`는 Excel source row에 대응하는 `source_key = risk-db:{source_row}`를 사용한다.

## 5. 시험 독립성에 대한 결론

현재 확인 결과를 근거로 다음은 주장할 수 없다.

> “KOLAS_RA_GT v1.0.0은 시험대상 시스템의 모든 runtime knowledge와 독립된 holdout dataset이다.”

RA retrieval DB와 GT 사이에 실질적인 content overlap이 확인되었기 때문이다.

다만 이 overlap이 각 GT row의 **원작성 계보가 동일함을 직접 증명하는 것은 아니다**. 현재 audit은 exact content overlap을 측정한 것이며, historical causal lineage까지 복원한 것은 아니다.

## 6. 공인시험 전 기관 결정 필요

### Option A — 현재 통합제품 end-to-end 시험

RA retrieval DB를 실제 제품 구성요소로 포함하여 시험한다.

이 경우:

- RA DB snapshot/hash를 시험조건으로 freeze한다.
- GT ↔ retrieval DB overlap을 시험기록에 명시한다.
- 성적서 결과를 “현재 통합제품의 end-to-end Hazard Identification 성능”으로 해석한다.
- “미학습 독립 데이터 일반화 성능”으로 표현하지 않는다.

### Option B — 독립성 통제 시험

GT와 중복되지 않는 별도 holdout dataset 또는 leakage-controlled retrieval snapshot/조건을 시험기관과 사전 합의한다.

이 경우:

- dataset 또는 SUT runtime condition이 변경된다.
- 새 identity/hash를 부여한다.
- 변경된 조건으로 필요한 regression, freeze 및 공식 성능시험을 다시 수행한다.

## 7. 권고

SEEXR 측에서 사후적으로 overlap row를 임의 삭제하거나 RA DB를 조용히 변경하지 않는다. 시험 시작 전에 시험기관이 측정하고자 하는 measurand와 독립성 요구 수준을 명시적으로 결정하고 그 결정에 맞춰 dataset/SUT snapshot을 freeze한다.

관련 decision은 `LAB_METHOD_DECISION_REGISTER.md`의 `DEC-METHOD-010`으로 관리한다.
