# SUT Freeze Candidate — SEEXR 위험성평가 AI

- Evidence ID: `EV-SUT-FREEZE-20261011`
- Candidate ID: `SEEXR-RA-SUT-RC-2026.10.11.2`
- 상태: `PRE_FREEZE`
- Machine evidence: `data/submission/evidence/sut_freeze_20261011/candidate.json`

> 이 문서는 최종 release가 아니라 **현재 구현으로부터 자동·직접 확인할 수 있는 값들을 미리 고정한 freeze candidate**다. 사람/시험기관 결정 또는 운영자-side DB snapshot이 필요한 필드는 명시적으로 null/PENDING으로 남긴다.

## 1. 현재 SUT source identity

| Component | Commit | Git tree | KOLAS relevant fingerprint | 상태 |
|---|---|---|---|---|
| Core | `279bc052830bca596183ecbe8378dd69d6722f15` | `91de2c76fa7cb96dc301ebf2e85abc8a560051d9` | `df38c2eab18eaed5d849643ce589523391a4cb02bdb24e11c32dd2599e4888f5` | relevant clean / full repo dirty |
| Agents | `86b7f1bfdefad8bac5eeee68e685277cd955f37c` | `62f1f1430a258adfed036bc4a815ca94f00e2f87` | `3dc2a32f7e79bf740a249854284b01072fa41e62209714060eb16237c21d997b` | clean |
| RA | `b400f87ffc483764e8a8857e12c188867425c2b2` | `db2089af3f6b50eff83ee19baf41d8f8949c893a` | 별도 repo commit으로 식별 | clean |
| Law | `ddb8a25f2f4526f2625cac57849593e7166ef667` | `da66acf84c366b491c7adb26e63a4a712b0771a0` | 별도 repo commit으로 식별 | clean |

Core의 full repo dirty 원인은 기존 untracked `apple-root-certs/` 1건이다. KOLAS relevant fingerprint에는 영향이 없지만 **최종 freeze에서는 full repo clean 또는 immutable build provenance를 요구한다.**

## 2. KOLAS model freeze candidate

일반 Green의 기본 alias는 변경하지 않는다. dedicated KOLAS deployment에만 다음 non-secret env 값을 주입한다.

```text
SEEXR_RISK_GPT41_MODEL=openai/gpt-4.1-2025-04-14
SEEXR_RISK_GPT41_MINI_MODEL=openai/gpt-4.1-mini-2025-04-14
SEEXR_RISK_GPT4O_MODEL=openai/gpt-4o-2024-11-20
```

검증 상태:

- Mastra `1.57.0` construction smoke: **3/3 PASS**
- 실제 OpenAI provider `Agent.generate()` smoke: **3/3 PASS**
- Agents 전체 test: **156/156 PASS**
- Mastra production build: **PASS**
- final deployment effective env verification: **PENDING**

## 3. Stateful dependency candidate

### RA

- rows: `6,443`
- embedded rows: `6,443 / 6,443`
- embedding model: `text-embedding-3-large`
- embedding version: `risk-search-v1`
- full content + vector snapshot SHA-256: `PENDING`

### Law

- laws: `17`
- law articles: `2,861`
- law files: `323`
- full content snapshot SHA-256: `PENDING`

현재 도구 보안경계에서는 row/vector 원문을 모델 프로세스로 반출하지 않고 full-content hash를 만드는 절차를 완료하지 않았다. 최종 snapshot은 DB 운영자 측에서 hash-only 방식으로 생성해야 한다.

## 4. Execution candidate

| 항목 | 현재 candidate |
|---|---|
| engineering base URL | `https://api.seexr.dev/api` |
| final accredited base URL | `PENDING` |
| agent | `risk-assessment` |
| protocol | `v2` |
| execution profile | `quick-fast-v1.0.0` |
| model mode | `fast` |
| reasoning style | `balanced` |
| RA method | `빈도강도법 5x4` |

## 5. Evaluation account gate

최종 계정은 다음을 만족해야 한다.

- active `Role.USER`
- admin/RBAC 없음
- Saved Instruction empty
- empty normalized text SHA-256 = `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- AI token allowance available

현재 내부 rehearsal account는 **Saved Instruction NON_EMPTY**이므로 final 계정으로 사용할 수 없다. plaintext는 기록하지 않았다. 이 조건은 official live preflight가 자동으로 차단한다.

## 6. Runtime candidate

- Linux `7.0.0-30-generic`, x86_64
- Node.js `v23.11.1`
- npm `11.10.1`
- Python `3.12.3`
- uv `0.8.5`
- final deployment image/OS immutable identity: `PENDING`

## 7. Final freeze gate

아래가 모두 충족되어야 `PRE_FREEZE → FROZEN`으로 승격한다.

- [ ] final accredited base URL 확정
- [ ] Core/Agents/RA/Law final commit/tag 확정
- [ ] SUT 네 repository full clean 또는 승인된 immutable build provenance
- [ ] final deployment에서 dated model env effective value 확인
- [ ] RA full content+vector snapshot hash 생성
- [ ] Law full content snapshot hash 생성
- [ ] dedicated empty-instruction 시험계정 provisioning
- [ ] `doctor --live --official --require-ready` PASS
- [ ] 동일 frozen source/runtime으로 시험 직전 AJQG PASS
- [ ] clean-room sample run PASS
- [ ] clean-room full 425-case run 및 seal verify PASS

현재는 이 조건을 모두 충족하지 않았으므로 release/tag를 임의로 생성하지 않는다.
