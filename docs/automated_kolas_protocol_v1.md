# Automated KOLAS Live Evaluation Protocol v1

Status: implementation candidate; testing-lab approval and SUT performance threshold are pending

## 1. Design goal

The official KOLAS demonstration must be executable from start to sealed report in one session.
The procedure therefore minimizes human intervention during the test and avoids any multi-day
human calibration dependency.

Target operator workflow:

1. Start official run.
2. Observe preflight and automatic Judge qualification.
3. Observe production SUT evaluation.
4. Receive automatically generated metrics, exceptions, audit log, and SHA-256 seal.

No case-by-case human labeling or adjudication is required during the official run.

## 2. Measurement claim

The method does NOT claim that an LLM Judge is a human-equivalent safety expert.

The primary measurand is:

> Reference-conformance of SEEXR generated risk assessment output under a frozen,
> pre-specified automated evaluation procedure.

The frozen procedure includes:
- reference dataset identity
- SUT identity and production source fingerprint
- deterministic parser/rules
- Judge model and prompt
- automatic Judge qualification suite
- matching and metric formulas
- acceptance / reporting rules

This framing avoids treating inter-LLM consensus as proof of human truth.

## 3. Replace human calibration with Automatic Judge Qualification Gate (AJQG)

Human calibration / two-expert adjudication is removed from the official live workflow.

Before any SUT cases are scored, the system runs an automatic control suite whose expected
decisions are known by construction.

### 3.1 Control families

A. Structured-output controls
- valid schema
- malformed / missing required fields
- duplicated IDs
- missing pair decisions

B. Semantic match positive controls
- exact reference-risk identity
- conservative rule-based paraphrase variants
- harmless word-order / wrapper changes

C. Semantic match negative controls
- deliberately unrelated hazard mechanism
- deliberately incompatible accident mechanism
- contradiction controls

D. Accident classification controls
- identical normalized accident class -> pass
- explicit swapped incompatible class -> fail

E. Mitigation controls
- valid control copied from reference -> pass
- mitigation removed -> fail
- mitigation reverses safe action -> fail
- generic non-actionable text -> specificity fail

F. Legal-basis controls
- reference legal basis copied -> relevant pass
- no legal basis -> presence fail
- deliberately invalid/nonexistent placeholder article -> relevance fail

G. Critical-safety controls
- explicit unsafe reversal such as “do not isolate power; work energized” -> critical true
- safe reference mitigation -> critical false

H. Robustness controls
- pair order reversal
- ID renaming
- whitespace / field-order perturbation
- repeated identical input

### 3.2 Qualification gate

Initial proposed automatic gate:
- structured completion >= 99.5%
- exact-positive semantic controls = 100%
- constructed-negative semantic controls >= 98%
- accident-control accuracy >= 98%
- mitigation-control accuracy >= 95%
- legal-control accuracy >= 95%
- critical-safety-control accuracy >= 98%
- repeated-control decision stability >= 98%
- no missing control family

If the Judge fails qualification, the official SUT run is not started.

The control suite is frozen and hash-identified before the test day.

## 4. Use checklist judgments instead of broad ordinal scoring

Replace semantic 0-4 and quality 0-2 ratings where possible with decomposed binary decisions.

### Stage 1: reference-to-generated match checklist
For every candidate pair:
- same hazardous event/mechanism? yes/no
- same work context/exposure target? yes/no
- accident mechanism compatible? yes/no

Python derives the final match from the frozen Boolean rule.

### Stage 2: matched mitigation checklist
Only for matched pairs:
- mitigation addresses the matched hazard mechanism? yes/no
- mitigation is actionable? yes/no
- mitigation is sufficiently specific? yes/no
- mitigation introduces unsafe advice? yes/no

### Stage 3: legal / safety diagnostics
- legal basis present: deterministic
- legal basis relevant: binary Judge
- critical unsafe instruction: binary Judge

This structure is easier to unit-test, easier to explain to an assessor, and less sensitive to
arbitrary Likert-score variation.

## 5. Official KOLAS metrics

### Primary
1. Hazard Semantic Identification Recall (`hazard_semantic_identification_recall`)
   - KOLAS-facing reference-level identification measurand.
   - A reference is identified only when at least one generated risk satisfies:
     `same_hazard_mechanism AND context_compatible`.
   - Accident compatibility alone never establishes a primary semantic identification.
   - Matching is many-to-one; Hungarian 1:1 uniqueness is not imposed on this Recall.
   - Denominator: reference risks for which the binary match matrix completed successfully.

### Secondary / diagnostic
2. Hazard Identification Accuracy (`hazard_identification_accuracy`)
   - Existing project/KPI-compatible supplementary metric.
   - Uses the broader rule `(same_hazard_mechanism AND context_compatible) OR accident_compatible`.
   - Kept for historical KPI continuity only and must not be presented as the KOLAS primary measurand.

3. Strict Reference Risk Coverage
   - Maximum-cardinality 1:1 matching over `same_hazard_mechanism AND context_compatible`.
   - Retained as a stricter uniqueness/completeness diagnostic.

4. SUT Completion Rate
   valid risk_assessment responses / requested cases

5. Schema & Numerical Consistency
   deterministic parser / range / arithmetic compliance

6. Accident Classification Agreement among strict matched risks
7. Mitigation Appropriateness among strict matched risks
8. Mitigation Actionability / Specificity among strict matched risks
9. Legal Basis Presence / Relevance

### Diagnostic only unless the testing laboratory explicitly approves otherwise
- unmatched/generated-risk rate
- unsupported-risk flag
- critical-safety-error flag

Reason: the frozen reference dataset may not be exhaustive, so an unmatched novel hazard must
not automatically be treated as an error.

## 6. Full 425-case live execution

To avoid sampling arguments, the preferred official mode remains all 425 frozen scenarios.

The current sequential pilot took about 48.6 minutes for 50 cases, which extrapolates to roughly
6.9 hours sequentially. The official runner therefore becomes an asynchronous bounded pipeline.

### 6.1 Concurrent DAG

Per case:
SUT -> parse/deterministic -> Judge match -> Python 1:1 match -> Judge matched-quality -> metrics

Global semaphores:
- SUT workers: initial 6-8
- Judge calls: initial 12-16
- per-case Judge pair batching: keep bounded
- adaptive backoff on 429 / 5xx

All stages retain atomic checkpoints and deterministic final ordering.

### 6.2 Runtime target

Engineering target for the complete 425-case official run:
- AJQG: <= 5 minutes
- SUT + Judge full evaluation: <= 60-90 minutes
- report / seal / verification: <= 5 minutes

This target must be load-tested before the KOLAS day and worker counts frozen after the benchmark.

## 7. One-click official mode

Add:

    kolas-llm-judge official-live

The command performs, in order:

1. Credential / network / model preflight
2. evaluator committed-clean check
3. dataset SHA-256 check
4. production SUT source fingerprint
5. Automatic Judge Qualification Gate
6. full 425-case concurrent evaluation
7. source fingerprint re-check
8. automatic report generation
9. automatic SHA-256 run seal
10. self-verification
11. final PASS / INVALID status

The operator should not make case-level decisions during the run.

## 8. Automatic failure handling

Failures are evidence, not interactive exceptions.

Examples:
- ask_user returned despite sufficient input -> SUT non-completion
- malformed XML -> schema failure
- transient 401 -> automatic auth refresh
- 429 / 5xx -> bounded automatic retry
- permanent API error -> case failure, continue
- Judge qualification failure -> abort before SUT scoring
- source fingerprint changed during run -> entire official candidate invalid

No failed case is silently retried until it happens to pass.

## 9. Live assessor dashboard

Show:
- phase: preflight / AJQG / full / seal
- completed / total
- success / failed
- current worker counts
- SUT queue / Judge queue
- elapsed / ETA
- retry counts
- schema compliance
- rolling primary metrics
- source fingerprint status
- current run hash / final seal status

Every visible value comes from the same canonical JSON artifacts used for the report.

## 10. Evidence package produced automatically

At completion:
- manifest.json
- qualification/summary.json
- qualification/control_results.csv
- report/summary.json
- report/case_metrics.csv
- report/failures.csv
- raw case checkpoints
- completion.json
- run_seal.json
- verification.json
- machine-readable environment / package versions

The test-lab-specific XLSX/PDF is generated from the sealed canonical artifacts, not from a
separate manual calculation.

## 11. Human involvement

### Before test day
- testing laboratory approves the measurand, control suite, and decision rules
- control suite is frozen once
- concurrency limits are load-tested and frozen

### On test day
- operator starts one command
- assessor observes the live dashboard
- no expert pair labeling
- no adjudication
- no manual score correction

### After run
- only administrative export / signature remains

## 12. Migration from current v0.5

Keep:
- frozen dataset / provenance
- production SUT client
- renewable auth
- parser and deterministic checks
- two-stage idea: match before matched quality
- Hungarian 1:1 matching
- manifests / source fingerprints
- atomic checkpoints
- retry logging
- canonical JSON/CSV reports
- run sealing

Replace:
- human_pairs.csv gate
- human_quality_pairs.csv gate
- human_generated.csv gate
- two-expert adjudication requirement
- 20-case x 3 human-alignment-style repeatability workflow
- ordinal Judge scoring where a binary checklist can be used

Add:
- AJQG control suite
- binary checklist Judge schema
- case-level asynchronous worker pool
- global API semaphores
- automatic official-live orchestration
- live dashboard
- pilot/full automatic sealing
- automatic final verification

## 13. Important scope note

This protocol is designed to be technically defensible and operationally compatible with a
same-day live test, but the accredited testing laboratory must agree that the frozen automated
Judge qualification and reference-conformance measurand are acceptable within its accredited
scope and chosen test method before the official accredited report is issued.

## 14. Implementation status (updated 2026-09-14)

Implemented:
- 104-control construction-defined AJQG suite and canonical SHA-256 identity
- GPT-5.6 Sol binary-checklist Judge
- live `qualify-judge` command and automatic gate artifacts
- KOLAS primary identification fixed to hazard mechanism + compatible work context; accident-only compatibility is excluded from the primary metric
- matched-only mitigation/legal quality evaluation and generated-risk critical safety diagnostics
- concurrency-safe rotating SEEXR authentication
- bounded case/SUT/Judge concurrency with atomic checkpoints and resume
- SUT non-completion vs evaluator/infrastructure failure taxonomy
- automated JSON/CSV aggregate report and automated method manifest
- `official-live` orchestration and Rich live dashboard
- automatic production source re-check, report, double-seal, and self-verification
- explicit `KOLAS_RA_GT` v1.0.0 dataset identity in addition to content SHA-256
- `compare-repeatability` for sealed repeated live-run semantic stability
- SUT performance threshold intentionally blocked until testing-lab approval

Frozen official runtime after production load testing (2026-09-09):
- runtime file: `configs/official_runtime_v1.yaml`
- case pipeline queue/concurrency: **24**
- production SUT concurrency: **6**
- Binary Judge global concurrency: **12**
- match chunk: **80 pairs**
- matched-quality chunk: **40 pairs**
- safety chunk: **50 generated risks**
- Judge: **gpt-5.6-sol / reasoning=medium / binary-checklist-v1**
- AJQG repeats: **2**

Freeze evidence: `20260909T022015Z-official-live-ebbcff7e` processed 50/50 cases in 255.38 s, SUT p95 36.72 s, harness retry/reconnect/auth-recovery 0, source stable, procedure valid, and final seal verified. This was approximately 32% faster than the 8/6/12 50-case run while keeping production SUT concurrency unchanged at 6.

Official mode reads these operational values only from `configs/official_runtime_v1.yaml`. CLI/environment overrides for Judge model/reasoning/concurrency, SUT method/model mode, chunks, or pipeline concurrency are development-only. `.env` supplies secrets/credentials, not the official test method. The runtime also freezes SHA-256 values for the dataset, AJQG seed/gate/control suite, binary Judge prompt, and binary rubric.

The remaining external/finalization steps before accredited use are: testing-lab review of the measurand/Rubric/repeatability policy, agreement on the SUT performance acceptance threshold, then a clean release candidate and 425-case full dry-run using the approved frozen runtime. The Sep-09 50-case run remains engineering/concurrency evidence and is not re-labelled as performance evidence for the Sep-14 primary-metric semantics.
