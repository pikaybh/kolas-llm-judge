# KOLAS 제출자료 무결성 Manifest

- 문서 ID: `KOLAS-DOC-013`
- 버전: `0.1-review`
- 상태: `REVIEW`
- 기준일: `2026-10-11`
- Machine manifest: `data/submission/submission_integrity_manifest_v1.json`
- Manifest version: `submission-integrity-v1`
- 상태: `CANDIDATE`

> 본 문서는 Phase 8 제출후보의 무결성 요약이다. 최종 공인 제출본이 아니다. 최종 SUT release/tag, 시험기관 계정, clean-room drill, HWP/HWPX/PDF가 확정된 뒤 machine manifest를 다시 생성하고 최종 checksum을 기록한다.

## 1. Candidate integrity identity

| 항목 | 값 |
|---|---|
| artifact count | `76` |
| artifact root SHA-256 | `7566872820ed951f05ad6ec18c7dc4aef5ead94dc3a3d35180056f4f8bb6c1ba` |
| machine manifest SHA-256 | `ffd5ab8b31c3e88aea5e4adf1495106f7aea95402b244f1ab12e989a8fc07426` |
| generated at UTC | `2026-10-11T03:39:06.938761+00:00` |
| repository committed base at generation | `08e0419c82d323f8fb2a3b9f2cf5ff60d630ba0f` |
| generator | `tools/build_submission_manifest.py` |
| generator SHA-256 | `e712d281006fab155ee758d7aedd727d012a9aef6d51a94d344c95fdc9884085` |
| hash algorithm | `SHA-256` |
| root record encoding | sorted `path\0sha256\0size\n` |

## 2. 검증 결과

Machine verifier 실행 결과:

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

76개 대상 중 하나라도 삭제되거나 내용/크기가 변경되면 검증은 실패한다.

## 3. 범위

포함 범위:

- 제출용 Markdown/템플릿(본 `13_INTEGRITY_MANIFEST.md` 제외)
- evaluator Python source
- official runtime / AJQG / rubric / provenance config
- Judge prompt
- canonical GT raw/scenario 및 GT provenance artifacts
- dependency lock / package metadata / `.env.example`
- manifest 생성 도구 및 GT provenance 도구
- 시험방법/compliance/evaluation 기술문서

제외 범위:

- 실제 `.env` 및 secret 값
- `runs/` 실험/응답 디렉터리
- `derived/` 분석 산출물
- untracked `docs/lab_handoff/`
- 본 `13_INTEGRITY_MANIFEST.md`
- 아직 생성되지 않은 최종 HWP/HWPX/PDF

본 문서를 root 대상에서 제외하는 이유는 machine manifest SHA와 artifact root를 본 문서가 기록하기 때문에 발생하는 자기참조를 방지하기 위해서다. 본 문서 자체의 최종 무결성은 Git commit/tag와 최종 HWP/PDF/전자자료 checksum layer에서 보호한다.

## 4. Artifact category summary

| 범주 | 파일 수 |
|---|---:|
| 제출 Markdown/템플릿 | 19 |
| Evaluator source | 30 |
| Config/Prompt | 9 |
| GT/Provenance data | 8 |
| Package/기술문서/도구 | 10 |

## 5. 전체 artifact checksum 목록

아래 표는 machine manifest의 76개 항목을 그대로 사람이 확인할 수 있게 전개한 것이다.

| # | Path | Size (bytes) | SHA-256 |
|---:|---|---:|---|
| 1 | `.env.example` | 1297 | `3c82cb21e47b3c458570bc5bc67db6ac814bf87ccbac4bfd9f3ad445d9e3c3f9` |
| 2 | `README.md` | 15030 | `82873969fb49f22724abb068412648c952fbadec4708e53e151655266c778f8c` |
| 3 | `configs/ajqg_gate_v1.yaml` | 437 | `2ee9934e921fa82b10697d6cf9ffca6e72f151a49159ac3aff7a8b7d17421a6b` |
| 4 | `configs/ajqg_seed_v1.yaml` | 3298 | `f0f11537d77555e55fe5ae143fa92e92ddc631da1d7a1711fe2f070ad38b8586` |
| 5 | `configs/evaluation.yaml` | 3016 | `6ae43cac40b1db1ef506ddfc3fcc980bfb61b90a78aac6e092ad26cb7f7fe580` |
| 6 | `configs/gt_provenance_schema_v1.yaml` | 1787 | `58d9ad6b9566b17bc114786b037e0efcd901ba9de316a5241f72fd4c06c03fe2` |
| 7 | `configs/official_runtime_v1.yaml` | 3002 | `bc49cde29d7da64185c6d2f4ea8311e8e4df3e82622ec47c4f80e60d0135ec1e` |
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
| 22 | `docs/submission_package/00_PHASE0_EVIDENCE_INVENTORY.md` | 18856 | `4fff8fa0cd7bd4305150da8c4721eedd51a4b92f493d4b5810958ea52908e409` |
| 23 | `docs/submission_package/01_TEST_METHOD.md` | 13340 | `63baa7bd96e5e6a427be1bfd0c8c9640b4ce0d38da9ae4ca5bd07a12b5dcb6ad` |
| 24 | `docs/submission_package/02_SYSTEM_UNDER_TEST.md` | 13757 | `d8f4942f613953f62112ab15a582383b7cd9cd13705d38a7fa880eea68dfab5f` |
| 25 | `docs/submission_package/03_INFERENCE_CONFIGURATION.md` | 12509 | `74a2f7e5da9a409fa0938f3efeb64507c9da37f05d5b15d6e94e7fc8e0bc58f1` |
| 26 | `docs/submission_package/04_GT_SPECIFICATION.md` | 13092 | `786b127ef77d84cff79836218cdaa621a9805b46271d6d0bee80c537d1717422` |
| 27 | `docs/submission_package/05_GT_SOURCE_PROVENANCE.md` | 12814 | `bf573130778e622479345959a5e6a176856eee0b1c5afd4e43ba8a081caf7fc8` |
| 28 | `docs/submission_package/08_EVALUATOR_SPECIFICATION.md` | 7603 | `e19a2ef15846b523ae634c745937647fd6e73d0e7ea8d31e13ff45d50fd53bb8` |
| 29 | `docs/submission_package/09_EVALUATOR_QUALIFICATION.md` | 7396 | `1879ad262dfaec181328ac27590823a1bdda973625c6ccc49cfa4e95df4d15ea` |
| 30 | `docs/submission_package/10_REPRODUCIBILITY_GUIDE.md` | 12069 | `50db2d432aba6a6fffcf78a21972a5f5a4bb770e849915c4b2dc9a2602cf2d96` |
| 31 | `docs/submission_package/11_API_ACCESS_GUIDE.md` | 13240 | `21d2590dd04e1789a839bc49847d3cbac9bd526a9141be4bba13e18da372938a` |
| 32 | `docs/submission_package/12_VERSION_MANIFEST.md` | 12985 | `5f8a52e91cbcc0f98ab2deac6e2701dfa086e2565457c637b737eeef844eb71e` |
| 33 | `docs/submission_package/14_CHANGE_CONTROL.md` | 9563 | `d66c3ad06a43f4f6119d01f8fa3330c155909812dbc2a7334a09f518cd9a1f89` |
| 34 | `docs/submission_package/DOCUMENT_REGISTER.md` | 3657 | `1eb62b8bb1f8fc3bce4f330ded08b5a9147774197bf32146225ab36a735a8570` |
| 35 | `docs/submission_package/HWP_HANDOFF_SPEC.md` | 7415 | `b336e549febab035a2aeabbe59d3721ab7b1ddc3823e5eeff7b1ea5ee75628a7` |
| 36 | `docs/submission_package/MASTER_PLAN.md` | 19110 | `764bf1c4f2512e8e64066ebdbe3caec2fc0ced64700a519c27ae739fee4c96eb` |
| 37 | `docs/submission_package/README.md` | 7762 | `7a3b979f77db90848f070213979b1c1bb012ceb9d3feab8aac7f4956d003bd7b` |
| 38 | `docs/submission_package/templates/GT_PROVENANCE_REGISTER_TEMPLATE.csv` | 370 | `7774b5985c0b9055c219119a30bfd8cfdb00f19635c6978fc0afce87b50c1a36` |
| 39 | `docs/submission_package/templates/SECTION_TEMPLATE.md` | 907 | `165f7bcc895d3e8f5d71dafec58fa0a983ed611f397b8fac7bd4f7a4724140fe` |
| 40 | `docs/testing_lab_method_and_rubric_v1.md` | 9514 | `86d37134e19b853ae586dd44f066184ac16ac17322884262289274e04a34dd16` |
| 41 | `prompts/judge_binary_v1.md` | 2255 | `97884ac7d7440b8e3843b0eee357478275871f949d4ef305b5c52a1eb3bad0bf` |
| 42 | `prompts/judge_v1.md` | 751 | `3bbe73a96c0c0bacf6a383c40de2047d78760abdc5a6fd233454597fe9a035b9` |
| 43 | `pyproject.toml` | 726 | `f826d884f7e0c0dbe0c1fc156c3e9030ac13e98b63e6579a74cf24b18aab39d5` |
| 44 | `src/kolas_llm_judge/__init__.py` | 42 | `a0ab02a688904925f1e7b0c6b3655f63378ed6e9094317469d5fb6842dc12343` |
| 45 | `src/kolas_llm_judge/automated_manifest.py` | 6754 | `190c9f63e07ca83a18b5c43f8f52f424bfed0916539dd09592c94dd416fa849b` |
| 46 | `src/kolas_llm_judge/automated_report.py` | 12625 | `d089edb2f059103a5492764ec899eb1e54f72ff5ccc54aaedb563c8bd10c7ac7` |
| 47 | `src/kolas_llm_judge/binary_evaluation.py` | 14207 | `92ecedad4d246f9e91c0b5e3baf68628f4de728a0df96df2e105da9bd1dc3adb` |
| 48 | `src/kolas_llm_judge/binary_human_calibration.py` | 29612 | `59b500189eb4267d514172ac08c988da2f19b3af0184aca55c19312b229e7572` |
| 49 | `src/kolas_llm_judge/binary_judge.py` | 11979 | `6523cd65eeee33e618cefecbb68a6cb1ec394e85ca40898b88d49e53b7470cef` |
| 50 | `src/kolas_llm_judge/calibration.py` | 42624 | `260372e85bea70db602117cbe5be48bd9656c718977843e0857e86da177f963c` |
| 51 | `src/kolas_llm_judge/cli.py` | 24580 | `7648eac69d1feb5e25ab4595edc0cee0da7b7ab92edccc52f6c9e3c00400cea7` |
| 52 | `src/kolas_llm_judge/dataset.py` | 6033 | `bcbf5d6b29b1b89e1c56502c0918719c5fc836d23b4bbab87f84f209434599cd` |
| 53 | `src/kolas_llm_judge/derived_analysis.py` | 8426 | `ddffe60865815b8bcffe00380e08e6bf88581160ec0bc25cb056d702a85574e4` |
| 54 | `src/kolas_llm_judge/deterministic.py` | 10162 | `72e8d073d72988d262aeddd907e3f469bc892d59a5c2b289dfe2a3d707e86d77` |
| 55 | `src/kolas_llm_judge/doctor.py` | 11659 | `7a41ab5bbd615127a004d4d0265915aad3a650898a9ba067678e298cd0666fa2` |
| 56 | `src/kolas_llm_judge/identification.py` | 3415 | `4f62b70e26cb37fa983f487d75a7ac9cffad1026dd202b7618574b1a136be71b` |
| 57 | `src/kolas_llm_judge/io_utils.py` | 1565 | `ccf901ad293af1ae7a16245540847e08a7c052a7a9433a5227429ae102ab00b8` |
| 58 | `src/kolas_llm_judge/judge.py` | 25729 | `6e37b29d184b658e66d6a853eeb0875b2bcef54b82edadd563e7e4f0dca334d4` |
| 59 | `src/kolas_llm_judge/manifest.py` | 14910 | `b9a2c03eee5a4490979eab3692d2f730365a34e2baf9df53054af2a90a8d3210` |
| 60 | `src/kolas_llm_judge/matching.py` | 4261 | `3ca23ee4cffc8d5333b29946c497f713d88cb26b02c86255ca10b069fa84d943` |
| 61 | `src/kolas_llm_judge/metrics.py` | 2576 | `062306281e7f3884c86ee4dd36858565db2af77138d39778c7cab19893f864f7` |
| 62 | `src/kolas_llm_judge/models.py` | 5486 | `786253ae6f453d5a01b992073f02577abf7ed9adab2c0791b22721136cde821c` |
| 63 | `src/kolas_llm_judge/official_live.py` | 11919 | `845a86cebc156c6844d31225650226292521f60bbe6352ddf5fa44d00e58064e` |
| 64 | `src/kolas_llm_judge/official_runtime.py` | 13195 | `0f012a4ffa35b9b2fb8794fa5eb599846b7d6ee89cd59e3d88c54a04b5f572f0` |
| 65 | `src/kolas_llm_judge/parallel_runner.py` | 14248 | `5e61273b1568da53c92be89a3de26a97437cbe2e34aba285a8b482080a316019` |
| 66 | `src/kolas_llm_judge/parser.py` | 5143 | `8f57878b18a2526c0df251026d70af9baf6a8399e071ecbd1ccc4a8642db3e45` |
| 67 | `src/kolas_llm_judge/qualification.py` | 10105 | `6d6cfe505f03cafada91fe5e571a6bdc1109a92d88003041a444d1c4d6c7ba20` |
| 68 | `src/kolas_llm_judge/qualification_controls.py` | 11084 | `be759e962a2625bc4515768096895bd8078557a3a752b12c6be1c8326d3fa5d5` |
| 69 | `src/kolas_llm_judge/repeatability.py` | 5964 | `6e39c3d345c165ab78f224b0521e821e9e73f09ef65456eb38074468bb069bc4` |
| 70 | `src/kolas_llm_judge/report.py` | 25280 | `b6b0028aba22e1eedcc5ea08ea7545afeb92f306cd8f9b1c1738e0a914978543` |
| 71 | `src/kolas_llm_judge/runner.py` | 22241 | `1a53a4ac32956c920183881e6d0b2ab015569f5daf1501e16bbc3fb3213c528f` |
| 72 | `src/kolas_llm_judge/seal.py` | 6908 | `c6b82efbb42bf7d425f7452cf764ed3c139b3c5304c958d73c70d8fe4e91014b` |
| 73 | `src/kolas_llm_judge/sut_client.py` | 25968 | `e4edbb19e11b5bb58482c3579a7f74fbf82c7bba3c1b428b98ba204ea4383d79` |
| 74 | `tools/build_submission_manifest.py` | 9545 | `e712d281006fab155ee758d7aedd727d012a9aef6d51a94d344c95fdc9884085` |
| 75 | `tools/gt_provenance.py` | 3714 | `a52d7e7c35ed87233d0f9e5555233e6cb744fbdff53313d654d95e70206cdf4f` |
| 76 | `uv.lock` | 173838 | `59502e93ca708512472ab858e78d22e3e4f06f5a8de63ddf9e51c8d3475c5c6f` |

## 6. GT 및 핵심 evaluator 교차확인

| 항목 | SHA-256 |
|---|---|
| GT raw | `b76c9efa718a0429f587b311d9e6e1d2107bf13101b0f91bc02a69e695ad142a` |
| scenarios | `2cdc1e8b9e05766d29790965bcf09c4015662daf8c70571209bccb4a15ee419c` |
| official runtime | `bc49cde29d7da64185c6d2f4ea8311e8e4df3e82622ec47c4f80e60d0135ec1e` |
| Judge prompt | `97884ac7d7440b8e3843b0eee357478275871f949d4ef305b5c52a1eb3bad0bf` |
| Judge rubric | `d6993b9c49a88e4d5389c8d72dde27d750d0880c57d2fd18d38e08ae3ae93a22` |
| evaluator source aggregate | `78152ba3c9df69b4dfc837b15380b9e25a2f132ab9d9abc75ba11337b582fbc1` |

`evaluator source aggregate`는 official runtime의 별도 frozen source identity이며, 위 76-file submission artifact root와 목적이 다르다.

## 7. Candidate와 Final의 구분

현재 manifest는 `CANDIDATE`다. 다음 항목은 아직 final freeze되지 않았다.

- final SUT Core/Agents/RA/Law release/tag
- RA embedding-inclusive DB snapshot
- Law DB snapshot
- final SUT base URL
- 시험기관 전용 계정/entitlement/Saved Instruction freeze
- 시험 직전 AJQG PASS
- 외부 clean-room reproduction PASS
- 기관 최종 행정정보/양식
- HWP/HWPX/PDF 최종 파일

따라서 현재 root를 “최종 공인 제출 checksum”으로 표현하지 않는다.

## 8. Final freeze 절차

1. Phase 9 clean-room drill과 Phase 2/7 미확정값을 종료한다.
2. 제출 Markdown을 `APPROVED` 상태로 정리한다.
3. 최종 HWP/HWPX/PDF를 생성한다.
4. final delivery artifact를 integrity scope에 추가한다.
5. machine manifest를 다시 생성·검증한다.
6. 최종 manifest SHA-256과 artifact root를 공문/전자자료 목록에 기재한다.
7. 최종 Git tag/release를 생성한다.
8. 최종 package를 read-only 보존하고 이후 변경은 `14_CHANGE_CONTROL.md`에 따른다.

## 9. 변경통제 연결

변경분류 및 재시험 규칙은 `14_CHANGE_CONTROL.md`를 따른다. 현재 candidate artifact가 변경되면 기존 root를 덮어쓰지 않고 새 manifest/revision을 만든다.
