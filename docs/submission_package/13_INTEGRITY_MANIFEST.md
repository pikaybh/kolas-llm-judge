# KOLAS 제출자료 무결성 Manifest

- 문서 ID: `KOLAS-DOC-013`
- 버전: `0.4-review`
- 상태: `REVIEW`
- 기준일: `2026-10-11`
- Machine manifest: `data/submission/submission_integrity_manifest_v1.json`
- Manifest schema: `submission-integrity-v1`
- 상태: `CANDIDATE`

> Phase 9 rehearsal 이후 evaluation-account readiness gate와 SUT model snapshot freeze 경로까지 반영한 최신 제출후보 무결성 요약이다. 최종 공인 제출 checksum은 아니다.

## 1. Candidate integrity identity

| 항목 | 값 |
|---|---|
| artifact count | `77` |
| artifact root SHA-256 | `993f2537abcf286089c84fd197ca9f3889ec0850fd13329212e07248b23ceffe` |
| machine manifest SHA-256 | `34a106dd829ae13612352157328b19f712f618e89be7390cf719aa8373713bbf` |
| generated at UTC | `2026-10-11T04:44:08.052879+00:00` |
| repository committed base at generation | `3fbb1eedf6d3af302ebbb305d2278cbe138fad18` |
| generator | `tools/build_submission_manifest.py` |
| generator SHA-256 | `0abce3b635e2b99fc7dba157b197181de9dc01a0a0dd3633f26b9416b8b594b6` |
| hash algorithm | `SHA-256` |
| root record encoding | sorted `path\0sha256\0size\n` |

## 2. 검증 결과

```text
ok = true
missing = []
mismatched = []
internal_root_valid = true
current_root_matches = true
```

검증 명령:

```bash
PYTHONPATH="$PWD:$PWD/src" uv run python tools/build_submission_manifest.py verify
```

77개 대상 중 하나라도 삭제되거나 내용/크기가 변경되면 검증은 실패한다.

## 3. 이번 revision의 주요 integrity-impact 변경

- official evaluator source aggregate가 account-readiness preflight 추가로 `0069d7c24a53339b7d586e435547544e8bf8d4a7c52395f730efbffefd76a701`로 갱신됨
- official runtime SHA-256이 `1be77e55532324f98d8f2835178a1c02ead325c4f94b4724bda5511d883511e3`로 갱신됨
- live official preflight가 Saved Instruction empty와 AI token allowance를 자동 검사함
- SUT Agents `86b7f1b`에 KOLAS dated model snapshot override 경로가 추가됨
- Core/Agents current relevant source fingerprint와 RA/Law live-state audit가 문서에 반영됨

## 4. 범위

포함: 제출 Markdown/템플릿(본 문서 제외), clean-room rehearsal evidence, evaluator source, config/prompt, canonical GT/provenance, dependency lock, 기술문서와 생성도구.

제외: 실제 `.env`/secret, `runs/`, `derived/`, untracked `docs/lab_handoff/`, 본 `13_INTEGRITY_MANIFEST.md`, 아직 생성되지 않은 최종 HWP/HWPX/PDF.

본 문서는 machine manifest SHA와 artifact root를 기록하므로 자기참조 방지를 위해 root 대상에서 제외한다.

## 5. Artifact category summary

| 범주 | 파일 수 |
|---|---:|
| 제출 Markdown/템플릿 | 20 |
| Evaluator source | 30 |
| Config/Prompt | 9 |
| GT/Provenance data | 8 |
| Package/기술문서/도구 | 10 |

## 6. 전체 artifact checksum 목록

| # | Path | Size (bytes) | SHA-256 |
|---:|---|---:|---|
| 1 | `.env.example` | 1297 | `3c82cb21e47b3c458570bc5bc67db6ac814bf87ccbac4bfd9f3ad445d9e3c3f9` |
| 2 | `README.md` | 15030 | `82873969fb49f22724abb068412648c952fbadec4708e53e151655266c778f8c` |
| 3 | `configs/ajqg_gate_v1.yaml` | 437 | `2ee9934e921fa82b10697d6cf9ffca6e72f151a49159ac3aff7a8b7d17421a6b` |
| 4 | `configs/ajqg_seed_v1.yaml` | 3298 | `f0f11537d77555e55fe5ae143fa92e92ddc631da1d7a1711fe2f070ad38b8586` |
| 5 | `configs/evaluation.yaml` | 3016 | `6ae43cac40b1db1ef506ddfc3fcc980bfb61b90a78aac6e092ad26cb7f7fe580` |
| 6 | `configs/gt_provenance_schema_v1.yaml` | 1787 | `58d9ad6b9566b17bc114786b037e0efcd901ba9de316a5241f72fd4c06c03fe2` |
| 7 | `configs/official_runtime_v1.yaml` | 3002 | `1be77e55532324f98d8f2835178a1c02ead325c4f94b4724bda5511d883511e3` |
| 8 | `configs/rubric_binary_v1.yaml` | 1226 | `d6993b9c49a88e4d5389c8d72dde27d750d0880c57d2fd18d38e08ae3ae93a22` |
| 9 | `configs/rubric_v1.yaml` | 1314 | `6e6f4eed6561475f8357fe430a3d30ec4214efc944bf5ba2f6396adc281630a6` |
| 10 | `data/cases/GT_CHANGELOG.md` | 2101 | `49ba52c6f181798620e5eac846b4ce94afaeef40b6eae65b1b60deef20f50661` |
| 11 | `data/cases/dataset_manifest.json` | 461 | `e7679fabc39f6c6abb7eb53fdc72a9374deb8b0e64add9cdff4e89ec1cfddc2a` |
| 12 | `data/cases/gt_lineage_index_v1.csv` | 37755 | `55c0aa75f8cc0ca542c1fb6755a06ed563f02b0150605a227f2539d907aefbd6` |
| 13 | `data/cases/gt_provenance_audit_manifest_v1.json` | 3063 | `ec5bd4f9fded546ac4f2671da5e610688e674193135c9fc1c3b9ef7ac9c3727c` |
| 14 | `data/cases/gt_provenance_register_v1.csv` | 190676 | `00b52d389e2afc170c4114ac0308075199beb94d33c725a1beed6b370a679f1c` |
| 15 | `data/cases/scenarios_v1.jsonl` | 484611 | `2cdc1e8b9e05766d29790965bcf09c4015662daf8c70571209bccb4a15ee419c` |
| 16 | `data/raw/PROVENANCE.md` | 754 | `571f5cf43ce7e309ac93cf1f4312879eff5f966c7dc457db601304939316367a` |
| 17 | `data/raw/kolas_v7_73_test.csv.bz2` | 52817 | `b76c9efa718a0429f587b311d9e6e1d2107bf13101b0f91bc02a69e695ad142a` |
| 18 | `docs/automated_kolas_protocol_v1.md` | 14146 | `848d621444721b7d8fc3f650f9dcbb53498c92702e5778bdce29f8153cf5a93b` |
| 19 | `docs/evaluation_spec.md` | 17541 | `ad821fa9c1037b7565943d4bd0d7baaac0b785ee3fed8a21dea5f1f2060e46d2` |
| 20 | `docs/kolas_compliance_plan_v1.md` | 7580 | `1cd45a71306ca1acd086bf5736930c100234cac8b38533224069a5c6de67d149` |
| 21 | `docs/submission_package/00_PHASE0_AUDIT_LOG.md` | 2513 | `0ccf2ec50e5045f8b7821fc3bc2c16d1b059a13cdea3a3ce2c2da143ce8c1847` |
| 22 | `docs/submission_package/00_PHASE0_EVIDENCE_INVENTORY.md` | 19911 | `91f8f221d7af10638c70794289e02a0bd260421811d098928fbfbbac8a26efd0` |
| 23 | `docs/submission_package/01_TEST_METHOD.md` | 13340 | `63baa7bd96e5e6a427be1bfd0c8c9640b4ce0d38da9ae4ca5bd07a12b5dcb6ad` |
| 24 | `docs/submission_package/02_SYSTEM_UNDER_TEST.md` | 14932 | `f5d6d6dfa6186d477105c63b4f874d7857b8a44b1f83f215520d54f6f17c3f8e` |
| 25 | `docs/submission_package/03_INFERENCE_CONFIGURATION.md` | 13140 | `df1079db7fa3e4ada3420d66488efdea74f344b58f995dba6c47707306722d12` |
| 26 | `docs/submission_package/04_GT_SPECIFICATION.md` | 13092 | `786b127ef77d84cff79836218cdaa621a9805b46271d6d0bee80c537d1717422` |
| 27 | `docs/submission_package/05_GT_SOURCE_PROVENANCE.md` | 12814 | `bf573130778e622479345959a5e6a176856eee0b1c5afd4e43ba8a081caf7fc8` |
| 28 | `docs/submission_package/08_EVALUATOR_SPECIFICATION.md` | 8166 | `02c9b022b31dab4098de51dcc44db12c05fe087a1a325370df54e57060b73123` |
| 29 | `docs/submission_package/09_EVALUATOR_QUALIFICATION.md` | 8010 | `31140ea35a2a6cfbebf5584917af148b3c377d7ae07d1de9c7847ddd4790bfa3` |
| 30 | `docs/submission_package/10_REPRODUCIBILITY_GUIDE.md` | 13229 | `f1787cd1be36cdbdda040cbba4a6f4e33d5490c037c4a34f945ca91574d93c33` |
| 31 | `docs/submission_package/11_API_ACCESS_GUIDE.md` | 14028 | `ca0b628d263ff528baa48f06e0b101bd8f41b83b078faf4890000dc037f60436` |
| 32 | `docs/submission_package/12_VERSION_MANIFEST.md` | 14309 | `055f52a0213dd4a72ffc099a8c902ad99ccad0206dcc2a8fa98633fa686f6630` |
| 33 | `docs/submission_package/14_CHANGE_CONTROL.md` | 9563 | `d66c3ad06a43f4f6119d01f8fa3330c155909812dbc2a7334a09f518cd9a1f89` |
| 34 | `docs/submission_package/CLEAN_ROOM_REHEARSAL_20261011.md` | 7690 | `006a4f67f843fd11b1886443ce3b33e68c8c8850c32acafeb6c92214d55b9e56` |
| 35 | `docs/submission_package/DOCUMENT_REGISTER.md` | 3908 | `80741ebff15146b1bde806fcb6cda21e5720a0d1fc688203768d1a04b9b283e6` |
| 36 | `docs/submission_package/HWP_HANDOFF_SPEC.md` | 7415 | `b336e549febab035a2aeabbe59d3721ab7b1ddc3823e5eeff7b1ea5ee75628a7` |
| 37 | `docs/submission_package/MASTER_PLAN.md` | 21145 | `a56ff3bd102d39f07dbb08b4d8f8bc2c9ea8ecdd8b946c1d00ca8515692aa5fb` |
| 38 | `docs/submission_package/README.md` | 7762 | `7a3b979f77db90848f070213979b1c1bb012ceb9d3feab8aac7f4956d003bd7b` |
| 39 | `docs/submission_package/templates/GT_PROVENANCE_REGISTER_TEMPLATE.csv` | 370 | `7774b5985c0b9055c219119a30bfd8cfdb00f19635c6978fc0afce87b50c1a36` |
| 40 | `docs/submission_package/templates/SECTION_TEMPLATE.md` | 907 | `165f7bcc895d3e8f5d71dafec58fa0a983ed611f397b8fac7bd4f7a4724140fe` |
| 41 | `docs/testing_lab_method_and_rubric_v1.md` | 9514 | `86d37134e19b853ae586dd44f066184ac16ac17322884262289274e04a34dd16` |
| 42 | `prompts/judge_binary_v1.md` | 2255 | `97884ac7d7440b8e3843b0eee357478275871f949d4ef305b5c52a1eb3bad0bf` |
| 43 | `prompts/judge_v1.md` | 751 | `3bbe73a96c0c0bacf6a383c40de2047d78760abdc5a6fd233454597fe9a035b9` |
| 44 | `pyproject.toml` | 726 | `f826d884f7e0c0dbe0c1fc156c3e9030ac13e98b63e6579a74cf24b18aab39d5` |
| 45 | `src/kolas_llm_judge/__init__.py` | 42 | `a0ab02a688904925f1e7b0c6b3655f63378ed6e9094317469d5fb6842dc12343` |
| 46 | `src/kolas_llm_judge/automated_manifest.py` | 6754 | `190c9f63e07ca83a18b5c43f8f52f424bfed0916539dd09592c94dd416fa849b` |
| 47 | `src/kolas_llm_judge/automated_report.py` | 12625 | `d089edb2f059103a5492764ec899eb1e54f72ff5ccc54aaedb563c8bd10c7ac7` |
| 48 | `src/kolas_llm_judge/binary_evaluation.py` | 14207 | `92ecedad4d246f9e91c0b5e3baf68628f4de728a0df96df2e105da9bd1dc3adb` |
| 49 | `src/kolas_llm_judge/binary_human_calibration.py` | 29612 | `59b500189eb4267d514172ac08c988da2f19b3af0184aca55c19312b229e7572` |
| 50 | `src/kolas_llm_judge/binary_judge.py` | 11979 | `6523cd65eeee33e618cefecbb68a6cb1ec394e85ca40898b88d49e53b7470cef` |
| 51 | `src/kolas_llm_judge/calibration.py` | 42624 | `260372e85bea70db602117cbe5be48bd9656c718977843e0857e86da177f963c` |
| 52 | `src/kolas_llm_judge/cli.py` | 24580 | `7648eac69d1feb5e25ab4595edc0cee0da7b7ab92edccc52f6c9e3c00400cea7` |
| 53 | `src/kolas_llm_judge/dataset.py` | 6033 | `bcbf5d6b29b1b89e1c56502c0918719c5fc836d23b4bbab87f84f209434599cd` |
| 54 | `src/kolas_llm_judge/derived_analysis.py` | 8426 | `ddffe60865815b8bcffe00380e08e6bf88581160ec0bc25cb056d702a85574e4` |
| 55 | `src/kolas_llm_judge/deterministic.py` | 10162 | `72e8d073d72988d262aeddd907e3f469bc892d59a5c2b289dfe2a3d707e86d77` |
| 56 | `src/kolas_llm_judge/doctor.py` | 13442 | `7e2cf0c89f0e58f2ddcc3f1f43d1a6c4cfe6262d6fb1db2fde3ecf93c294b082` |
| 57 | `src/kolas_llm_judge/identification.py` | 3415 | `4f62b70e26cb37fa983f487d75a7ac9cffad1026dd202b7618574b1a136be71b` |
| 58 | `src/kolas_llm_judge/io_utils.py` | 1565 | `ccf901ad293af1ae7a16245540847e08a7c052a7a9433a5227429ae102ab00b8` |
| 59 | `src/kolas_llm_judge/judge.py` | 25729 | `6e37b29d184b658e66d6a853eeb0875b2bcef54b82edadd563e7e4f0dca334d4` |
| 60 | `src/kolas_llm_judge/manifest.py` | 14910 | `b9a2c03eee5a4490979eab3692d2f730365a34e2baf9df53054af2a90a8d3210` |
| 61 | `src/kolas_llm_judge/matching.py` | 4261 | `3ca23ee4cffc8d5333b29946c497f713d88cb26b02c86255ca10b069fa84d943` |
| 62 | `src/kolas_llm_judge/metrics.py` | 2576 | `062306281e7f3884c86ee4dd36858565db2af77138d39778c7cab19893f864f7` |
| 63 | `src/kolas_llm_judge/models.py` | 5486 | `786253ae6f453d5a01b992073f02577abf7ed9adab2c0791b22721136cde821c` |
| 64 | `src/kolas_llm_judge/official_live.py` | 11919 | `845a86cebc156c6844d31225650226292521f60bbe6352ddf5fa44d00e58064e` |
| 65 | `src/kolas_llm_judge/official_runtime.py` | 13195 | `0f012a4ffa35b9b2fb8794fa5eb599846b7d6ee89cd59e3d88c54a04b5f572f0` |
| 66 | `src/kolas_llm_judge/parallel_runner.py` | 14248 | `5e61273b1568da53c92be89a3de26a97437cbe2e34aba285a8b482080a316019` |
| 67 | `src/kolas_llm_judge/parser.py` | 5143 | `8f57878b18a2526c0df251026d70af9baf6a8399e071ecbd1ccc4a8642db3e45` |
| 68 | `src/kolas_llm_judge/qualification.py` | 10105 | `6d6cfe505f03cafada91fe5e571a6bdc1109a92d88003041a444d1c4d6c7ba20` |
| 69 | `src/kolas_llm_judge/qualification_controls.py` | 11084 | `be759e962a2625bc4515768096895bd8078557a3a752b12c6be1c8326d3fa5d5` |
| 70 | `src/kolas_llm_judge/repeatability.py` | 5964 | `6e39c3d345c165ab78f224b0521e821e9e73f09ef65456eb38074468bb069bc4` |
| 71 | `src/kolas_llm_judge/report.py` | 25280 | `b6b0028aba22e1eedcc5ea08ea7545afeb92f306cd8f9b1c1738e0a914978543` |
| 72 | `src/kolas_llm_judge/runner.py` | 22241 | `1a53a4ac32956c920183881e6d0b2ab015569f5daf1501e16bbc3fb3213c528f` |
| 73 | `src/kolas_llm_judge/seal.py` | 6908 | `c6b82efbb42bf7d425f7452cf764ed3c139b3c5304c958d73c70d8fe4e91014b` |
| 74 | `src/kolas_llm_judge/sut_client.py` | 27828 | `45cbc9a94f1f4e7497d4bd55826eaf5a032ab03f33e86494d82126cab4d42e1d` |
| 75 | `tools/build_submission_manifest.py` | 9609 | `0abce3b635e2b99fc7dba157b197181de9dc01a0a0dd3633f26b9416b8b594b6` |
| 76 | `tools/gt_provenance.py` | 3714 | `a52d7e7c35ed87233d0f9e5555233e6cb744fbdff53313d654d95e70206cdf4f` |
| 77 | `uv.lock` | 173838 | `59502e93ca708512472ab858e78d22e3e4f06f5a8de63ddf9e51c8d3475c5c6f` |

## 7. Candidate root history

| 단계 | Artifact 수 | Root SHA-256 | 의미 |
|---|---:|---|---|
| Phase 8 최초 candidate | 76 | `7566872820ed951f05ad6ec18c7dc4aef5ead94dc3a3d35180056f4f8bb6c1ba` | fresh clone에서 동일 root 재현 |
| Phase 9 clean-room evidence 반영 | 77 | `6473c87dd1f3d55aeecf243d96eb95c9f0322d8614b6d5480125cb033c0f72fd` | clean-room rehearsal/등록부 반영 |
| Account gate + model snapshot freeze revision | 77 | `993f2537abcf286089c84fd197ca9f3889ec0850fd13329212e07248b23ceffe` | 현재 최신 candidate |

이전 manifest는 Git 이력에서 감사 가능하다.

## 8. 핵심 identity 교차확인

| 항목 | SHA-256 / identity |
|---|---|
| GT raw | `b76c9efa718a0429f587b311d9e6e1d2107bf13101b0f91bc02a69e695ad142a` |
| scenarios | `2cdc1e8b9e05766d29790965bcf09c4015662daf8c70571209bccb4a15ee419c` |
| official runtime | `1be77e55532324f98d8f2835178a1c02ead325c4f94b4724bda5511d883511e3` |
| Judge prompt | `97884ac7d7440b8e3843b0eee357478275871f949d4ef305b5c52a1eb3bad0bf` |
| Judge rubric | `d6993b9c49a88e4d5389c8d72dde27d750d0880c57d2fd18d38e08ae3ae93a22` |
| evaluator source aggregate | `0069d7c24a53339b7d586e435547544e8bf8d4a7c52395f730efbffefd76a701` |
| Core relevant source | `df38c2eab18eaed5d849643ce589523391a4cb02bdb24e11c32dd2599e4888f5` |
| Agents relevant source | `3dc2a32f7e79bf740a249854284b01072fa41e62209714060eb16237c21d997b` |

## 9. 아직 final이 아닌 이유

- final SUT immutable deployment/tag 및 effective dated-snapshot env freeze 미완료
- dedicated empty-instruction institution account provisioning 미완료
- 유효 Judge OpenAI credential 기반 fresh AJQG 미완료
- RA embedding-inclusive full snapshot hash 미완료
- Law DB full content snapshot hash 미완료
- live clean-room sample/full run 미완료
- 독립 제3자 sign-off 미완료
- 최종 HWP/HWPX/PDF 미생성

따라서 현재 root를 최종 공인 제출 checksum으로 표현하지 않는다.

## 10. Final freeze

Phase 1/2/7/9의 외부·운영 미확정값을 닫고 live clean-room sign-off를 완료한 뒤 final HWP/HWPX/PDF까지 scope에 추가해 manifest를 재생성하고 최종 Git tag/release를 생성한다. 이후 변경은 `14_CHANGE_CONTROL.md`를 따른다.
