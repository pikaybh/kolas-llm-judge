# KOLAS 제출자료 무결성 Manifest

- 문서 ID: `KOLAS-DOC-013`
- 버전: `0.8-review`
- 상태: `REVIEW`
- 기준일: `2026-10-11`
- Machine manifest: `data/submission/submission_integrity_manifest_v1.json`
- Manifest schema: `submission-integrity-v1`
- 상태: `CANDIDATE`

> current-source AJQG, SUT freeze candidate, 시험기관 Method Decision Register, RA/Law deterministic DB content fingerprints까지 반영한 최신 제출후보 무결성 요약이다. 최종 공인 제출 checksum은 아니다.

## 1. Candidate integrity identity

| 항목 | 값 |
|---|---|
| artifact count | `84` |
| artifact root SHA-256 | `21b2c5af538f7a7779162a1e09d0b3909da276caf6b8f25617fd0a16ccf6cdcf` |
| machine manifest SHA-256 | `433a1b3a0e90d06fab5d363f2aa876d1ac15b6aa9c2d5a150d2f1a6791a807ff` |
| generated at UTC | `2026-10-11T05:26:02.363314+00:00` |
| repository committed base at generation | `182c9aa27f1e9712a0a935c3afa776d9af68f7d2` |
| generator SHA-256 | `4114c1efbbb954cffd96e1104d197bb04cfe25b53eceebeda53b9dce87bfab8b` |

## 2. 주요 bound evidence

| Evidence | Identity |
|---|---|
| fresh AJQG binding | `abac8aeefc86112e02e230247c42b3292c780d859c29c6d12b61a09db12354cb` |
| SUT freeze candidate JSON | `172668ec893ad15bc112fd6e5e06b881252d339499afe9c0fa21ad9ec49e506a` |
| Stateful DB fingerprint evidence | `0309bc33b89de41fa78b3666ca3a88788765e302f1f7c131bf5e9ad6c779f79f` |
| RA storage+vector root | `67f28e5dcc57b8de983852601c2cd0d4ae7ac89a53140447522a01d806c8f340` |
| RA behavioral root | `b681fac625e154b02443bacff72ba4ae6fb4d3c8d5609c68da58b30da20ce5db` |
| Law content root | `5116d414d9d3c9cdb90a09bee6bd948434b019ca54328a3511e7a9c1bc641f57` |
| Method Decision Register | `METHOD-DECISION-REGISTER-20261011` / `PROPOSAL` |

## 3. 범위

포함: 제출 Markdown/템플릿(본 문서 제외), evaluator source/config/prompt, canonical GT/provenance, fresh AJQG evidence, SUT freeze candidate, stateful DB content fingerprints, method decision register, dependency lock, 기술문서와 생성도구.

제외: 실제 `.env`/secret, `runs/`, `derived/`, untracked `docs/lab_handoff/`, 본 `13_INTEGRITY_MANIFEST.md`, 아직 생성되지 않은 최종 HWP/HWPX/PDF.

## 4. Artifact category summary

| 범주 | 파일 수 |
|---|---:|
| 제출 Markdown/템플릿 | 22 |
| Evaluator source | 30 |
| Config/Prompt | 9 |
| AJQG evidence | 3 |
| SUT freeze evidence | 1 |
| Stateful DB evidence | 1 |
| GT/Provenance data | 8 |
| Package/기술문서/도구 | 10 |

## 5. 전체 artifact checksum 목록

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
| 18 | `data/submission/evidence/ajqg_20261011/binding.json` | 1463 | `abac8aeefc86112e02e230247c42b3292c780d859c29c6d12b61a09db12354cb` |
| 19 | `data/submission/evidence/ajqg_20261011/control_results.csv` | 27346 | `d58600def63198640101bb740ed3406efe53f06c7203d7a69d41e048b070caf6` |
| 20 | `data/submission/evidence/ajqg_20261011/summary.json` | 6374 | `5ad49cbda247ceab93edaf60942ed86f31d32f557fe3403455c99c24aac6b623` |
| 21 | `data/submission/evidence/stateful_snapshot_20261011/content_fingerprints.json` | 2334 | `0309bc33b89de41fa78b3666ca3a88788765e302f1f7c131bf5e9ad6c779f79f` |
| 22 | `data/submission/evidence/sut_freeze_20261011/candidate.json` | 4912 | `172668ec893ad15bc112fd6e5e06b881252d339499afe9c0fa21ad9ec49e506a` |
| 23 | `docs/automated_kolas_protocol_v1.md` | 14146 | `848d621444721b7d8fc3f650f9dcbb53498c92702e5778bdce29f8153cf5a93b` |
| 24 | `docs/evaluation_spec.md` | 17541 | `ad821fa9c1037b7565943d4bd0d7baaac0b785ee3fed8a21dea5f1f2060e46d2` |
| 25 | `docs/kolas_compliance_plan_v1.md` | 7580 | `1cd45a71306ca1acd086bf5736930c100234cac8b38533224069a5c6de67d149` |
| 26 | `docs/submission_package/00_PHASE0_AUDIT_LOG.md` | 2513 | `0ccf2ec50e5045f8b7821fc3bc2c16d1b059a13cdea3a3ce2c2da143ce8c1847` |
| 27 | `docs/submission_package/00_PHASE0_EVIDENCE_INVENTORY.md` | 20665 | `22ae470a19aa79ec8f1f2780e3c31e1a187a5be7ab01b423574cbc6bffa9ae24` |
| 28 | `docs/submission_package/01_TEST_METHOD.md` | 13340 | `63baa7bd96e5e6a427be1bfd0c8c9640b4ce0d38da9ae4ca5bd07a12b5dcb6ad` |
| 29 | `docs/submission_package/02_SYSTEM_UNDER_TEST.md` | 15174 | `541d7e894184236c41dc69a8b7ea460c4cef8a44504322ad482e1a982df51f85` |
| 30 | `docs/submission_package/03_INFERENCE_CONFIGURATION.md` | 13140 | `df1079db7fa3e4ada3420d66488efdea74f344b58f995dba6c47707306722d12` |
| 31 | `docs/submission_package/04_GT_SPECIFICATION.md` | 13092 | `786b127ef77d84cff79836218cdaa621a9805b46271d6d0bee80c537d1717422` |
| 32 | `docs/submission_package/05_GT_SOURCE_PROVENANCE.md` | 12814 | `bf573130778e622479345959a5e6a176856eee0b1c5afd4e43ba8a081caf7fc8` |
| 33 | `docs/submission_package/08_EVALUATOR_SPECIFICATION.md` | 8279 | `abab06f03b45b132eb135a689727f25f986c2f971e14ce60925d90d5ccd040e1` |
| 34 | `docs/submission_package/09_EVALUATOR_QUALIFICATION.md` | 9356 | `e2e9ff4ec84957db97cfe8955da6f51893b7f7ac19d1145deb645328b7a4e778` |
| 35 | `docs/submission_package/10_REPRODUCIBILITY_GUIDE.md` | 13229 | `f1787cd1be36cdbdda040cbba4a6f4e33d5490c037c4a34f945ca91574d93c33` |
| 36 | `docs/submission_package/11_API_ACCESS_GUIDE.md` | 14028 | `ca0b628d263ff528baa48f06e0b101bd8f41b83b078faf4890000dc037f60436` |
| 37 | `docs/submission_package/12_VERSION_MANIFEST.md` | 15994 | `445bc954191dd4a47b982c477c613d800a1da976904c5d6156f4f07cdbe85f6b` |
| 38 | `docs/submission_package/14_CHANGE_CONTROL.md` | 9563 | `d66c3ad06a43f4f6119d01f8fa3330c155909812dbc2a7334a09f518cd9a1f89` |
| 39 | `docs/submission_package/CLEAN_ROOM_REHEARSAL_20261011.md` | 9297 | `42a41103dd9b51a20ac389d51aebd45084f2c69d857e9fa31e977dbd614396f4` |
| 40 | `docs/submission_package/DOCUMENT_REGISTER.md` | 4940 | `a5f82142cfe4281f97e4c18dcd4a2e7e9835fb6c3970c2e098d3a5d816865ff2` |
| 41 | `docs/submission_package/HWP_HANDOFF_SPEC.md` | 7415 | `b336e549febab035a2aeabbe59d3721ab7b1ddc3823e5eeff7b1ea5ee75628a7` |
| 42 | `docs/submission_package/LAB_METHOD_DECISION_REGISTER.md` | 9573 | `9018f69e6611b2c50fed52b34d14e304174c1d7ebc44bf2548835b16f2d5ee17` |
| 43 | `docs/submission_package/MASTER_PLAN.md` | 22196 | `5139924ba37686b8791ceb0979ecb91c89518dcb56de345dda717e3ac741fcc7` |
| 44 | `docs/submission_package/README.md` | 7953 | `875eef31471daf3701d183ae86c035bd983f8d6f0787b598610d3d216895af3b` |
| 45 | `docs/submission_package/SUT_FREEZE_CANDIDATE.md` | 5682 | `41c36f2c638f87fb35a68f075718480214fe3e12cbb785bf1f8bcf4f65c228e5` |
| 46 | `docs/submission_package/templates/GT_PROVENANCE_REGISTER_TEMPLATE.csv` | 370 | `7774b5985c0b9055c219119a30bfd8cfdb00f19635c6978fc0afce87b50c1a36` |
| 47 | `docs/submission_package/templates/SECTION_TEMPLATE.md` | 907 | `165f7bcc895d3e8f5d71dafec58fa0a983ed611f397b8fac7bd4f7a4724140fe` |
| 48 | `docs/testing_lab_method_and_rubric_v1.md` | 9514 | `86d37134e19b853ae586dd44f066184ac16ac17322884262289274e04a34dd16` |
| 49 | `prompts/judge_binary_v1.md` | 2255 | `97884ac7d7440b8e3843b0eee357478275871f949d4ef305b5c52a1eb3bad0bf` |
| 50 | `prompts/judge_v1.md` | 751 | `3bbe73a96c0c0bacf6a383c40de2047d78760abdc5a6fd233454597fe9a035b9` |
| 51 | `pyproject.toml` | 726 | `f826d884f7e0c0dbe0c1fc156c3e9030ac13e98b63e6579a74cf24b18aab39d5` |
| 52 | `src/kolas_llm_judge/__init__.py` | 42 | `a0ab02a688904925f1e7b0c6b3655f63378ed6e9094317469d5fb6842dc12343` |
| 53 | `src/kolas_llm_judge/automated_manifest.py` | 6754 | `190c9f63e07ca83a18b5c43f8f52f424bfed0916539dd09592c94dd416fa849b` |
| 54 | `src/kolas_llm_judge/automated_report.py` | 12625 | `d089edb2f059103a5492764ec899eb1e54f72ff5ccc54aaedb563c8bd10c7ac7` |
| 55 | `src/kolas_llm_judge/binary_evaluation.py` | 14207 | `92ecedad4d246f9e91c0b5e3baf68628f4de728a0df96df2e105da9bd1dc3adb` |
| 56 | `src/kolas_llm_judge/binary_human_calibration.py` | 29612 | `59b500189eb4267d514172ac08c988da2f19b3af0184aca55c19312b229e7572` |
| 57 | `src/kolas_llm_judge/binary_judge.py` | 11979 | `6523cd65eeee33e618cefecbb68a6cb1ec394e85ca40898b88d49e53b7470cef` |
| 58 | `src/kolas_llm_judge/calibration.py` | 42624 | `260372e85bea70db602117cbe5be48bd9656c718977843e0857e86da177f963c` |
| 59 | `src/kolas_llm_judge/cli.py` | 24580 | `7648eac69d1feb5e25ab4595edc0cee0da7b7ab92edccc52f6c9e3c00400cea7` |
| 60 | `src/kolas_llm_judge/dataset.py` | 6033 | `bcbf5d6b29b1b89e1c56502c0918719c5fc836d23b4bbab87f84f209434599cd` |
| 61 | `src/kolas_llm_judge/derived_analysis.py` | 8426 | `ddffe60865815b8bcffe00380e08e6bf88581160ec0bc25cb056d702a85574e4` |
| 62 | `src/kolas_llm_judge/deterministic.py` | 10162 | `72e8d073d72988d262aeddd907e3f469bc892d59a5c2b289dfe2a3d707e86d77` |
| 63 | `src/kolas_llm_judge/doctor.py` | 13442 | `7e2cf0c89f0e58f2ddcc3f1f43d1a6c4cfe6262d6fb1db2fde3ecf93c294b082` |
| 64 | `src/kolas_llm_judge/identification.py` | 3415 | `4f62b70e26cb37fa983f487d75a7ac9cffad1026dd202b7618574b1a136be71b` |
| 65 | `src/kolas_llm_judge/io_utils.py` | 1565 | `ccf901ad293af1ae7a16245540847e08a7c052a7a9433a5227429ae102ab00b8` |
| 66 | `src/kolas_llm_judge/judge.py` | 25729 | `6e37b29d184b658e66d6a853eeb0875b2bcef54b82edadd563e7e4f0dca334d4` |
| 67 | `src/kolas_llm_judge/manifest.py` | 14910 | `b9a2c03eee5a4490979eab3692d2f730365a34e2baf9df53054af2a90a8d3210` |
| 68 | `src/kolas_llm_judge/matching.py` | 4261 | `3ca23ee4cffc8d5333b29946c497f713d88cb26b02c86255ca10b069fa84d943` |
| 69 | `src/kolas_llm_judge/metrics.py` | 2576 | `062306281e7f3884c86ee4dd36858565db2af77138d39778c7cab19893f864f7` |
| 70 | `src/kolas_llm_judge/models.py` | 5486 | `786253ae6f453d5a01b992073f02577abf7ed9adab2c0791b22721136cde821c` |
| 71 | `src/kolas_llm_judge/official_live.py` | 11919 | `845a86cebc156c6844d31225650226292521f60bbe6352ddf5fa44d00e58064e` |
| 72 | `src/kolas_llm_judge/official_runtime.py` | 13195 | `0f012a4ffa35b9b2fb8794fa5eb599846b7d6ee89cd59e3d88c54a04b5f572f0` |
| 73 | `src/kolas_llm_judge/parallel_runner.py` | 14248 | `5e61273b1568da53c92be89a3de26a97437cbe2e34aba285a8b482080a316019` |
| 74 | `src/kolas_llm_judge/parser.py` | 5143 | `8f57878b18a2526c0df251026d70af9baf6a8399e071ecbd1ccc4a8642db3e45` |
| 75 | `src/kolas_llm_judge/qualification.py` | 10105 | `6d6cfe505f03cafada91fe5e571a6bdc1109a92d88003041a444d1c4d6c7ba20` |
| 76 | `src/kolas_llm_judge/qualification_controls.py` | 11084 | `be759e962a2625bc4515768096895bd8078557a3a752b12c6be1c8326d3fa5d5` |
| 77 | `src/kolas_llm_judge/repeatability.py` | 5964 | `6e39c3d345c165ab78f224b0521e821e9e73f09ef65456eb38074468bb069bc4` |
| 78 | `src/kolas_llm_judge/report.py` | 25280 | `b6b0028aba22e1eedcc5ea08ea7545afeb92f306cd8f9b1c1738e0a914978543` |
| 79 | `src/kolas_llm_judge/runner.py` | 22241 | `1a53a4ac32956c920183881e6d0b2ab015569f5daf1501e16bbc3fb3213c528f` |
| 80 | `src/kolas_llm_judge/seal.py` | 6908 | `c6b82efbb42bf7d425f7452cf764ed3c139b3c5304c958d73c70d8fe4e91014b` |
| 81 | `src/kolas_llm_judge/sut_client.py` | 27828 | `45cbc9a94f1f4e7497d4bd55826eaf5a032ab03f33e86494d82126cab4d42e1d` |
| 82 | `tools/build_submission_manifest.py` | 10112 | `4114c1efbbb954cffd96e1104d197bb04cfe25b53eceebeda53b9dce87bfab8b` |
| 83 | `tools/gt_provenance.py` | 3714 | `a52d7e7c35ed87233d0f9e5555233e6cb744fbdff53313d654d95e70206cdf4f` |
| 84 | `uv.lock` | 173838 | `59502e93ca708512472ab858e78d22e3e4f06f5a8de63ddf9e51c8d3475c5c6f` |

## 6. Candidate root history

| 단계 | Artifact 수 | Root SHA-256 | 의미 |
|---|---:|---|---|
| Phase 8 최초 candidate | 76 | `7566872820ed951f05ad6ec18c7dc4aef5ead94dc3a3d35180056f4f8bb6c1ba` | fresh clone 재현 |
| Phase 9 clean-room 반영 | 77 | `6473c87dd1f3d55aeecf243d96eb95c9f0322d8614b6d5480125cb033c0f72fd` | rehearsal/등록부 반영 |
| Fresh AJQG normalized evidence | 80 | `08569120520fc4033325fb45b1ca0b9d8d9773637aa87f433a22e3aa9430a3dc` | current-source Judge qualification |
| SUT freeze + method decision prep | 83 | `000bfe35d3b8a566f86f7d4ea803735cc7ff1ca0a34c0ee5502b9faec17d114d` | PRE_FREEZE 및 기관 선택표 |
| Stateful DB content fingerprints | 84 | `21b2c5af538f7a7779162a1e09d0b3909da276caf6b8f25617fd0a16ccf6cdcf` | 현재 최신 candidate |

## 7. 아직 final이 아닌 이유

- 시험기관 method decision 미승인
- final accredited base URL/tag 및 effective dated-model env freeze 미완료
- dedicated empty-instruction 시험계정 provisioning 미완료
- final freeze 직전 RA/Law fingerprint 재캡처 미완료
- live clean-room sample/full run 미완료
- 독립 operator sign-off 미완료
- 최종 HWP/HWPX/PDF 미생성

RA/Law **content identity hash는 확보**되었다. 기관이 DB 자체를 로컬 복원해야 한다고 요구하는 경우에만 restore-capable backup artifact가 추가된다.
