# Phase 0 Audit Log

- 문서 ID: `KOLAS-AUDIT-000`
- 기준일: `2026-10-11`
- 상태: `REVIEW`

## 수행한 검증

- [x] canonical raw GT와 scenario 파일의 SHA-256 재계산 및 manifest 대조
- [x] raw row/scenario/reference count 재계산
- [x] raw GT header에서 source/provenance 필드 존재 여부 확인
- [x] official runtime/prompt/rubric/Judge 구현 경로 확인
- [x] evaluator aggregate source hash 재계산 및 runtime 기대값 대조
- [x] `validate_official_runtime` 직접 실행 — PASS
- [x] 2026-09-09 full run의 completion/final status/seal/qualification 확인
- [x] strict semantic derived result 및 10-case repeatability artifact 확인
- [x] SUT client의 실제 endpoint/auth/retry 경로 확인
- [x] 과거 full run SUT source fingerprint/HEAD/dirty 상태 확인
- [x] 과거 Agents tracked HEAD의 quick-fast 핵심 model declaration 확인
- [x] 현재 quick-fast workflow가 직접 호출하는 모델 구성 확인
- [x] Judge OpenAI Responses 호출 인자 확인
- [x] OpenAI 공식 GPT-5.6 Sol / Responses / Fast mode 문서 확인
- [x] Git ignored raw/run/derived artifact 범위 확인
- [x] credential 변수명과 `.env` ignore 상태 확인(값은 열람/기록하지 않음)
- [x] focused reproducibility regression tests 25건 실행 — 25 PASS

## 재현에 사용한 주요 명령 범주

- `sha256sum`
- Python csv/json count validation
- `validate_official_runtime(...)`
- `git cat-file`, `git grep`, `git show`로 historical tracked source 확인
- run `manifest.json`, `completion.json`, `final_status.json`, `verification.json`, `report/summary.json` 구조 검토
- `pytest` focused reproducibility suite

## 주의사항

이 감사는 기존 파일을 변경하지 않는 read-only 검증을 우선했다. 문서 작성 외에는 GT, run artifact, SUT source에 변경을 가하지 않았다. 실제 secret 값은 출력하거나 문서화하지 않았다.
## 2026-10-11 Phase 3 재감사 정정

Phase 3 GT provenance 감사에서 Phase 0 Evidence Inventory의 raw GT hash, original workbook 기록 hash 및 raw header 표기가 실제 canonical evidence와 불일치한 전사 오류임을 확인했다. 실제 canonical raw/scenario 파일은 변경되지 않았으며, `PROVENANCE.md`, 초기 commit `ca16726`, dataset manifest 및 official runtime은 올바른 `b76c9efa...` / `d12c7d68...` 계보를 일관되게 유지하고 있었다. Evidence Inventory의 해당 값을 정정하고 본 감사로그에 정정 사실을 남긴다.
