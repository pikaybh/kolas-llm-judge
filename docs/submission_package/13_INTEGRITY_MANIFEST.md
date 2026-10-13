# KOLAS 제출자료 무결성 Manifest

- 문서 ID: `KOLAS-DOC-013`
- 버전: `1.0-review`
- 상태: `REVIEW`
- 기준일: `2026-10-13`
- Machine manifest: `data/submission/submission_integrity_manifest_v1.json`
- Manifest schema: `submission-integrity-v1`
- Machine manifest 상태: `CANDIDATE`

> 본 문서는 2026-10-13 시험기관 요청사항 대응표, 시험 데이터 독립성/RA retrieval 중복 감사, 실행환경·반복시험 정책까지 포함한 현재 제출후보의 무결성 요약이다. 최종 공인 제출 checksum은 아니며 final SUT/시험조건 승인 후 다시 생성한다.

## 1. Candidate integrity identity

| 항목 | 값 |
|---|---|
| artifact count | `92` |
| artifact root SHA-256 | `41747e87279d57fda83be9ed24d74410042f7a82c5fdd1f5c3a32411f26b30cc` |
| machine manifest SHA-256 | `2461d0609b0a181c50025aa337d0e625de6c5bb06cfaa73517f091ce520c7adf` |
| generated at UTC | `2026-10-13T09:22:04.324905+00:00` |
| repository base HEAD at generation | `a0f84f32e6ac24514bf718a40fb32adcc41a11b2` |
| generator SHA-256 | `7a1fd31271cf7d1768e57c6d20e833291861a1bb2e8e307d8512a07347b691e8` |

## 2. 주요 bound evidence

| Evidence | Identity / 상태 |
|---|---|
| Fresh AJQG binding | `abac8aeefc86112e02e230247c42b3292c780d859c29c6d12b61a09db12354cb` / PASS |
| SUT freeze candidate | `data/submission/evidence/sut_freeze_20261011/candidate.json` / PRE_FREEZE |
| Stateful DB fingerprint | `data/submission/evidence/stateful_snapshot_20261011/content_fingerprints.json` / PRE_FREEZE |
| GT↔RA overlap audit | `data/submission/evidence/gt_ra_overlap_audit_20261013.json` / REVIEW |
| SUT source/fine-tuning indicator audit | `data/submission/evidence/sut_gt_source_overlap_audit_20261013.json` / REVIEW |
| Method Decision Register | `METHOD-DECISION-REGISTER-20261011` / PROPOSAL; `DEC-METHOD-010` 추가 |
| Finalization Blocker Register | `FINALIZATION-BLOCKERS-20261011` / ACTIVE; `BLK-LAB-010` 추가 |
| HWP Assembly Map | `HWP-ASSEMBLY-MAP-20261011` / READY_FOR_FINAL_INPUTS |

## 3. 범위

포함: 제출 Markdown/템플릿(본 문서 제외), evaluator source/config/prompt, canonical GT/provenance, AJQG evidence, SUT freeze/stateful DB evidence, 2026-10-13 GT↔RA overlap 및 source audit evidence, 시험기관 요청사항 crosswalk, 실행환경/반복정책, dependency lock, 기술문서와 생성도구.

제외: 실제 `.env`/secret, `runs/`, `derived/`, 사용자 보존용 untracked `docs/lab_handoff/`, 본 `13_INTEGRITY_MANIFEST.md`, 아직 생성되지 않은 최종 HWP/HWPX/PDF.

본 문서는 machine manifest SHA와 artifact root를 기록하므로 자기참조 방지를 위해 root 대상에서 제외한다.

## 4. Artifact category summary

| 범주 | 파일 수 |
|---|---:|
| 제출 Markdown/템플릿 | 28 |
| Evaluator source | 30 |
| Config/Prompt | 9 |
| AJQG evidence | 3 |
| SUT/Stateful/Overlap evidence | 4 |
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
| 21 | `data/submission/evidence/gt_ra_overlap_audit_20261013.json` | 11203 | `d622c3ec2e0cd5eec5dda0fdede80ec51d99083ef42a96ddb2c7858955308e87` |
| 22 | `data/submission/evidence/stateful_snapshot_20261011/content_fingerprints.json` | 2334 | `0309bc33b89de41fa78b3666ca3a88788765e302f1f7c131bf5e9ad6c779f79f` |
| 23 | `data/submission/evidence/sut_freeze_20261011/candidate.json` | 4912 | `172668ec893ad15bc112fd6e5e06b881252d339499afe9c0fa21ad9ec49e506a` |
| 24 | `data/submission/evidence/sut_gt_source_overlap_audit_20261013.json` | 897 | `3bbf6d655a083281856529630ec5c1419a3def66a0728c196a4617b4947f9d56` |
| 25 | `docs/automated_kolas_protocol_v1.md` | 14146 | `848d621444721b7d8fc3f650f9dcbb53498c92702e5778bdce29f8153cf5a93b` |
| 26 | `docs/evaluation_spec.md` | 17541 | `ad821fa9c1037b7565943d4bd0d7baaac0b785ee3fed8a21dea5f1f2060e46d2` |
| 27 | `docs/kolas_compliance_plan_v1.md` | 7580 | `1cd45a71306ca1acd086bf5736930c100234cac8b38533224069a5c6de67d149` |
| 28 | `docs/submission_package/00_PHASE0_AUDIT_LOG.md` | 2513 | `0ccf2ec50e5045f8b7821fc3bc2c16d1b059a13cdea3a3ce2c2da143ce8c1847` |
| 29 | `docs/submission_package/00_PHASE0_EVIDENCE_INVENTORY.md` | 20687 | `b9c11e35e7b33556653f14db604214bf316c4c161a1813eb33778bc347847d27` |
| 30 | `docs/submission_package/01_TEST_METHOD.md` | 13628 | `6364f4f4057e376164a2afeb98b00b372fb79f9a94048a2d1f15a38ea3abf9fb` |
| 31 | `docs/submission_package/02_SYSTEM_UNDER_TEST.md` | 15174 | `541d7e894184236c41dc69a8b7ea460c4cef8a44504322ad482e1a982df51f85` |
| 32 | `docs/submission_package/03_INFERENCE_CONFIGURATION.md` | 13140 | `df1079db7fa3e4ada3420d66488efdea74f344b58f995dba6c47707306722d12` |
| 33 | `docs/submission_package/04_GT_SPECIFICATION.md` | 13182 | `7e8c9f1d659afa2da6a737e43aeeecfa196c50ffbb5a36e1e743a4e506c2b0eb` |
| 34 | `docs/submission_package/05_GT_SOURCE_PROVENANCE.md` | 13136 | `7e3550cbdfe872a4b3fdc6ebbcbdba965778d15f6978e7d6ffbd16ed327c6991` |
| 35 | `docs/submission_package/08_EVALUATOR_SPECIFICATION.md` | 8279 | `abab06f03b45b132eb135a689727f25f986c2f971e14ce60925d90d5ccd040e1` |
| 36 | `docs/submission_package/09_EVALUATOR_QUALIFICATION.md` | 9356 | `e2e9ff4ec84957db97cfe8955da6f51893b7f7ac19d1145deb645328b7a4e778` |
| 37 | `docs/submission_package/10_REPRODUCIBILITY_GUIDE.md` | 13229 | `f1787cd1be36cdbdda040cbba4a6f4e33d5490c037c4a34f945ca91574d93c33` |
| 38 | `docs/submission_package/11_API_ACCESS_GUIDE.md` | 14028 | `ca0b628d263ff528baa48f06e0b101bd8f41b83b078faf4890000dc037f60436` |
| 39 | `docs/submission_package/12_VERSION_MANIFEST.md` | 15994 | `445bc954191dd4a47b982c477c613d800a1da976904c5d6156f4f07cdbe85f6b` |
| 40 | `docs/submission_package/14_CHANGE_CONTROL.md` | 9563 | `d66c3ad06a43f4f6119d01f8fa3330c155909812dbc2a7334a09f518cd9a1f89` |
| 41 | `docs/submission_package/15_TEST_DATA_INDEPENDENCE_AUDIT.md` | 5576 | `af3ad784a6cb2b77bb9701cdcc6d5465ab9b06665e81d9a359dc26d0ce8151af` |
| 42 | `docs/submission_package/16_EXECUTION_ENVIRONMENT_REPEAT_POLICY.md` | 5498 | `9686fc71deaf7baeb256422637faa96cf6c0558cf550ee082122ed423fcb8e70` |
| 43 | `docs/submission_package/17_KOLAS_REQUEST_CROSSWALK.md` | 5835 | `7ac131d1c99283824933a6324efeb8d9f4c24e7486b5ebc308cc6ed394a172ea` |
| 44 | `docs/submission_package/CLEAN_ROOM_REHEARSAL_20261011.md` | 9297 | `42a41103dd9b51a20ac389d51aebd45084f2c69d857e9fa31e977dbd614396f4` |
| 45 | `docs/submission_package/DOCUMENT_REGISTER.md` | 6776 | `69091ae55527f33f54ef0506415cf3d76f4868e39e9f2a8478d9d34c0f0c2769` |
| 46 | `docs/submission_package/FINALIZATION_BLOCKER_REGISTER.md` | 6874 | `23b1593a21190dcd86eef432fa369f08b485953f5e4ff9e181bb1e8bbfefa9e3` |
| 47 | `docs/submission_package/HWP_ASSEMBLY_MAP.md` | 5677 | `d8caadbb3b8f9cd4770cf05fcf4467b995eb3fd9d26068782d836fdacfbe4436` |
| 48 | `docs/submission_package/HWP_HANDOFF_SPEC.md` | 7415 | `b336e549febab035a2aeabbe59d3721ab7b1ddc3823e5eeff7b1ea5ee75628a7` |
| 49 | `docs/submission_package/LAB_METHOD_DECISION_REGISTER.md` | 11382 | `57dfc69b23e490bade83c09af82262dae8852dc48a77fe82aff664d5246dde11` |
| 50 | `docs/submission_package/MASTER_PLAN.md` | 22759 | `85566846babbe999663a46d7d6d3365679f4019cd2c8f09b406bf3f9ae28f503` |
| 51 | `docs/submission_package/PLACEHOLDER_AUDIT.md` | 3994 | `f5960e9560b50cc37fd0d69df8db2195017925813289ba9de31a47a8d63c1218` |
| 52 | `docs/submission_package/README.md` | 8520 | `68d4f47859363bf902dcd2372503aac796db3fef916bae7e5a9583d96aac48ca` |
| 53 | `docs/submission_package/SUT_FREEZE_CANDIDATE.md` | 5682 | `41c36f2c638f87fb35a68f075718480214fe3e12cbb785bf1f8bcf4f65c228e5` |
| 54 | `docs/submission_package/templates/GT_PROVENANCE_REGISTER_TEMPLATE.csv` | 370 | `7774b5985c0b9055c219119a30bfd8cfdb00f19635c6978fc0afce87b50c1a36` |
| 55 | `docs/submission_package/templates/SECTION_TEMPLATE.md` | 907 | `165f7bcc895d3e8f5d71dafec58fa0a983ed611f397b8fac7bd4f7a4724140fe` |
| 56 | `docs/testing_lab_method_and_rubric_v1.md` | 9514 | `86d37134e19b853ae586dd44f066184ac16ac17322884262289274e04a34dd16` |
| 57 | `prompts/judge_binary_v1.md` | 2255 | `97884ac7d7440b8e3843b0eee357478275871f949d4ef305b5c52a1eb3bad0bf` |
| 58 | `prompts/judge_v1.md` | 751 | `3bbe73a96c0c0bacf6a383c40de2047d78760abdc5a6fd233454597fe9a035b9` |
| 59 | `pyproject.toml` | 726 | `f826d884f7e0c0dbe0c1fc156c3e9030ac13e98b63e6579a74cf24b18aab39d5` |
| 60 | `src/kolas_llm_judge/__init__.py` | 42 | `a0ab02a688904925f1e7b0c6b3655f63378ed6e9094317469d5fb6842dc12343` |
| 61 | `src/kolas_llm_judge/automated_manifest.py` | 6754 | `190c9f63e07ca83a18b5c43f8f52f424bfed0916539dd09592c94dd416fa849b` |
| 62 | `src/kolas_llm_judge/automated_report.py` | 12625 | `d089edb2f059103a5492764ec899eb1e54f72ff5ccc54aaedb563c8bd10c7ac7` |
| 63 | `src/kolas_llm_judge/binary_evaluation.py` | 14207 | `92ecedad4d246f9e91c0b5e3baf68628f4de728a0df96df2e105da9bd1dc3adb` |
| 64 | `src/kolas_llm_judge/binary_human_calibration.py` | 29612 | `59b500189eb4267d514172ac08c988da2f19b3af0184aca55c19312b229e7572` |
| 65 | `src/kolas_llm_judge/binary_judge.py` | 11979 | `6523cd65eeee33e618cefecbb68a6cb1ec394e85ca40898b88d49e53b7470cef` |
| 66 | `src/kolas_llm_judge/calibration.py` | 42624 | `260372e85bea70db602117cbe5be48bd9656c718977843e0857e86da177f963c` |
| 67 | `src/kolas_llm_judge/cli.py` | 24580 | `7648eac69d1feb5e25ab4595edc0cee0da7b7ab92edccc52f6c9e3c00400cea7` |
| 68 | `src/kolas_llm_judge/dataset.py` | 6033 | `bcbf5d6b29b1b89e1c56502c0918719c5fc836d23b4bbab87f84f209434599cd` |
| 69 | `src/kolas_llm_judge/derived_analysis.py` | 8426 | `ddffe60865815b8bcffe00380e08e6bf88581160ec0bc25cb056d702a85574e4` |
| 70 | `src/kolas_llm_judge/deterministic.py` | 10162 | `72e8d073d72988d262aeddd907e3f469bc892d59a5c2b289dfe2a3d707e86d77` |
| 71 | `src/kolas_llm_judge/doctor.py` | 13442 | `7e2cf0c89f0e58f2ddcc3f1f43d1a6c4cfe6262d6fb1db2fde3ecf93c294b082` |
| 72 | `src/kolas_llm_judge/identification.py` | 3415 | `4f62b70e26cb37fa983f487d75a7ac9cffad1026dd202b7618574b1a136be71b` |
| 73 | `src/kolas_llm_judge/io_utils.py` | 1565 | `ccf901ad293af1ae7a16245540847e08a7c052a7a9433a5227429ae102ab00b8` |
| 74 | `src/kolas_llm_judge/judge.py` | 25729 | `6e37b29d184b658e66d6a853eeb0875b2bcef54b82edadd563e7e4f0dca334d4` |
| 75 | `src/kolas_llm_judge/manifest.py` | 14910 | `b9a2c03eee5a4490979eab3692d2f730365a34e2baf9df53054af2a90a8d3210` |
| 76 | `src/kolas_llm_judge/matching.py` | 4261 | `3ca23ee4cffc8d5333b29946c497f713d88cb26b02c86255ca10b069fa84d943` |
| 77 | `src/kolas_llm_judge/metrics.py` | 2576 | `062306281e7f3884c86ee4dd36858565db2af77138d39778c7cab19893f864f7` |
| 78 | `src/kolas_llm_judge/models.py` | 5486 | `786253ae6f453d5a01b992073f02577abf7ed9adab2c0791b22721136cde821c` |
| 79 | `src/kolas_llm_judge/official_live.py` | 11919 | `845a86cebc156c6844d31225650226292521f60bbe6352ddf5fa44d00e58064e` |
| 80 | `src/kolas_llm_judge/official_runtime.py` | 13195 | `0f012a4ffa35b9b2fb8794fa5eb599846b7d6ee89cd59e3d88c54a04b5f572f0` |
| 81 | `src/kolas_llm_judge/parallel_runner.py` | 14248 | `5e61273b1568da53c92be89a3de26a97437cbe2e34aba285a8b482080a316019` |
| 82 | `src/kolas_llm_judge/parser.py` | 5143 | `8f57878b18a2526c0df251026d70af9baf6a8399e071ecbd1ccc4a8642db3e45` |
| 83 | `src/kolas_llm_judge/qualification.py` | 10105 | `6d6cfe505f03cafada91fe5e571a6bdc1109a92d88003041a444d1c4d6c7ba20` |
| 84 | `src/kolas_llm_judge/qualification_controls.py` | 11084 | `be759e962a2625bc4515768096895bd8078557a3a752b12c6be1c8326d3fa5d5` |
| 85 | `src/kolas_llm_judge/repeatability.py` | 5964 | `6e39c3d345c165ab78f224b0521e821e9e73f09ef65456eb38074468bb069bc4` |
| 86 | `src/kolas_llm_judge/report.py` | 25280 | `b6b0028aba22e1eedcc5ea08ea7545afeb92f306cd8f9b1c1738e0a914978543` |
| 87 | `src/kolas_llm_judge/runner.py` | 22241 | `1a53a4ac32956c920183881e6d0b2ab015569f5daf1501e16bbc3fb3213c528f` |
| 88 | `src/kolas_llm_judge/seal.py` | 6908 | `c6b82efbb42bf7d425f7452cf764ed3c139b3c5304c958d73c70d8fe4e91014b` |
| 89 | `src/kolas_llm_judge/sut_client.py` | 27828 | `45cbc9a94f1f4e7497d4bd55826eaf5a032ab03f33e86494d82126cab4d42e1d` |
| 90 | `tools/build_submission_manifest.py` | 10619 | `7a1fd31271cf7d1768e57c6d20e833291861a1bb2e8e307d8512a07347b691e8` |
| 91 | `tools/gt_provenance.py` | 3714 | `a52d7e7c35ed87233d0f9e5555233e6cb744fbdff53313d654d95e70206cdf4f` |
| 92 | `uv.lock` | 173838 | `59502e93ca708512472ab858e78d22e3e4f06f5a8de63ddf9e51c8d3475c5c6f` |

## 6. Candidate root history

| 단계 | Artifact 수 | Root SHA-256 | 의미 |
|---|---:|---|---|
| Phase 8 최초 candidate | 76 | `7566872820ed951f05ad6ec18c7dc4aef5ead94dc3a3d35180056f4f8bb6c1ba` | fresh clone 재현 |
| Phase 9 clean-room 반영 | 77 | `6473c87dd1f3d55aeecf243d96eb95c9f0322d8614b6d5480125cb033c0f72fd` | rehearsal/등록부 반영 |
| Fresh AJQG normalized evidence | 80 | `08569120520fc4033325fb45b1ca0b9d8d9773637aa87f433a22e3aa9430a3dc` | current-source Judge qualification |
| SUT freeze + method decision prep | 83 | `000bfe35d3b8a566f86f7d4ea803735cc7ff1ca0a34c0ee5502b9faec17d114d` | PRE_FREEZE 및 기관 선택표 |
| Stateful DB content fingerprints | 84 | `21b2c5af538f7a7779162a1e09d0b3909da276caf6b8f25617fd0a16ccf6cdcf` | RA/Law deterministic content identity |
| HWP finalization preparation | 87 | `0e8900887d6ddbee2bb63162b7f6d58e459f79a3533a15b84ae3caf46c8f3ef6` | 2026-10-11 candidate |
| KOLAS request/independence audit | 92 | `41747e87279d57fda83be9ed24d74410042f7a82c5fdd1f5c3a32411f26b30cc` | 2026-10-13 GT↔RA overlap, HW/SW·repeat policy, one-stop crosswalk 반영 |

## 7. 아직 final이 아닌 이유

- `LAB_METHOD_DECISION_REGISTER.md`의 시험기관 승인 미완료
- `DEC-METHOD-010` / `BLK-LAB-010`: GT↔RA retrieval DB overlap의 시험조건·해석 미승인
- final accredited base URL/tag 및 effective model env freeze 미완료
- dedicated empty-instruction 시험계정 provisioning 미완료
- final freeze 직전 RA/Law fingerprint 재캡처 미완료
- live clean-room sample/full run 미완료
- HWP 행정정보 및 최종 HWP/HWPX/PDF 미확정

위 blocker를 닫기 전에는 현재 root를 최종 공인 제출 checksum으로 사용하지 않는다.
