# KOLAS 문서 등록부

상태값: `NOT_STARTED` / `DRAFT` / `REVIEW` / `APPROVED` / `FROZEN`

> Canonical experiment repository: `/home/pikaybh/Sandbox/kolas-llm-judge`
> SUT repositories such as `/srv/green-server/seexr-api-core` and `/srv/green-server/seexr-api-agents` are **시험대상/참조 증적**이며 본 제출 패키지의 canonical 저장소가 아니다.

| ID | Markdown | 내용 | HWP 반영 위치 | 상태 | 선행조건 |
|---|---|---|---|---|---|
| KOLAS-DOC-001 | `01_TEST_METHOD.md` | 시험 범위·지표·판정·계산식 | 붙임 1 | REVIEW | Phase 0 완료; 시험기관 method 승인 대기 |
| KOLAS-DOC-002 | `02_SYSTEM_UNDER_TEST.md` | SUT 구성·서비스·버전 | 붙임 1 | REVIEW | Phase 2 audit 완료; final deployment freeze 대기 |
| KOLAS-DOC-003 | `03_INFERENCE_CONFIGURATION.md` | 모델·reasoning·sampling·runtime 설정 | 붙임 2 | REVIEW | Phase 2 audit 완료; model snapshot policy 대기 |
| KOLAS-DOC-004 | `04_GT_SPECIFICATION.md` | GT 스키마·ID·freeze | 붙임 3 | REVIEW | Phase 3 integrity/spec audit 완료; GT는 연구실 검증 완료 데이터 |
| KOLAS-DOC-005 | `05_GT_SOURCE_PROVENANCE.md` | GT 근거자료와 traceability | 붙임 3 | REVIEW | file lineage 843/843; GT는 연구실 검증 완료; source provenance는 별도 추적정보 |
| KOLAS-DOC-006 | `06_EXPERT_VALIDATION_PROTOCOL.md` | 기존 연구실 검증 사실 기록 | 붙임 3 | NOT_REQUIRED | 신규 전문가 검증 절차는 수행하지 않음 |
| KOLAS-DOC-007 | `07_GT_RELIABILITY_REPORT.md` | 일치도·신뢰도·consensus 결과 | 붙임 3 | NOT_STARTED | 전문가 독립평가 완료 |
| KOLAS-DOC-008 | `08_EVALUATOR_SPECIFICATION.md` | Judge/판정 시스템 명세 | 붙임 4 | NOT_STARTED | evaluator 코드 감사 |
| KOLAS-DOC-009 | `09_EVALUATOR_QUALIFICATION.md` | Judge 적격성/반복성 검증 | 붙임 4 | NOT_STARTED | control set 확정 |
| KOLAS-DOC-010 | `10_REPRODUCIBILITY_GUIDE.md` | 설치부터 full run까지 재현 절차 | 붙임 5 | NOT_STARTED | runner package 준비 |
| KOLAS-DOC-011 | `11_API_ACCESS_GUIDE.md` | endpoint·auth·권한·오류 대응 | 붙임 5 | NOT_STARTED | 시험기관 계정 전략 |
| KOLAS-DOC-012 | `12_VERSION_MANIFEST.md` | repo/model/prompt/schema/runtime 버전 | 붙임 6 | REVIEW | audit snapshot 작성; final freeze 필드 대기 |
| KOLAS-DOC-013 | `13_INTEGRITY_MANIFEST.md` | 파일 목록·SHA-256 | 붙임 6/7 | NOT_STARTED | final package candidate |
| KOLAS-DOC-014 | `14_CHANGE_CONTROL.md` | 변경 승인·영향·재시험 규칙 | 붙임 6 | NOT_STARTED | version policy |

## 공통 metadata

각 문서 상단에 아래 값을 기록한다.

```text
문서 ID:
제목:
버전:
상태:
작성자:
검토자:
승인자:
기준일:
Evidence IDs:
관련 Git commit/tag:
관련 GT version:
관련 evaluator version:
```

## Evidence ID 규칙 권장안

- `EV-SUT-###` — SUT 코드/설정/배포 증적
- `EV-GT-###` — GT 및 source provenance
- `EV-EXP-###` — 전문가 검증/서명/통계
- `EV-EVAL-###` — evaluator/Judge 증적
- `EV-RUN-###` — 실제 시험 run/raw 결과
- `EV-API-###` — API contract/auth 증적
- `EV-INT-###` — checksum/version/integrity

Evidence registry 파일 형식과 저장 위치는 Phase 0에서 실제 자료 위치를 확인한 뒤 확정한다.
