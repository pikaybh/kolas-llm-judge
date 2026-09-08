from __future__ import annotations

from pydantic import BaseModel, Field


class ReferenceRisk(BaseModel):
    reference_id: str
    source_row: int
    hazard: str
    accident_types: list[str] = Field(default_factory=list)
    likelihood: int | None = None
    severity: int | None = None
    risk_score: int | None = None
    mitigation: str | None = None
    legal_basis: str | None = None


class ScenarioInput(BaseModel):
    process: str
    subprocess: str | None = None
    equipment: list[str] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)


class EvaluationScenario(BaseModel):
    case_id: str
    source_rows: list[int]
    input: ScenarioInput
    references: list[ReferenceRisk]


class DatasetManifest(BaseModel):
    source_file: str
    source_sha256: str
    source_rows: int
    scenario_count: int
    reference_count: int
    grouping: list[str]
    cases_sha256: str

class GeneratedRisk(BaseModel):
    generated_id: str
    source_item_id: str | None = None
    process: str | None = None
    subprocess: str | None = None
    hazard: str
    risk_cause: str | None = None
    accident_types: list[str] = Field(default_factory=list)
    likelihood: int | None = None
    severity: int | None = None
    risk_score: int | None = None
    risk_level_verbal: str | None = None
    mitigation: str | None = None
    post_likelihood: int | None = None
    post_severity: int | None = None
    post_risk_score: int | None = None
    post_risk_level_verbal: str | None = None
    legal_basis: str | None = None


class ParsedRiskAssessment(BaseModel):
    method: str | None = None
    process_name: str | None = None
    equipment: list[str] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    risks: list[GeneratedRisk] = Field(default_factory=list)
    xml: str
    trailing_text: str = ""


class DeterministicRiskCheck(BaseModel):
    generated_id: str
    schema_valid: bool
    frequency_in_range: bool | None = None
    severity_in_range: bool | None = None
    score_math_correct: bool | None = None
    post_frequency_in_range: bool | None = None
    post_severity_in_range: bool | None = None
    post_score_math_correct: bool | None = None
    post_risk_nonincreasing: bool | None = None
    errors: list[str] = Field(default_factory=list)


class DeterministicAssessmentResult(BaseModel):
    xml_parse_success: bool
    method: str | None = None
    item_count: int = 0
    schema_valid_items: int = 0
    checks: list[DeterministicRiskCheck] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

class PairMatchJudgeResult(BaseModel):
    # Compact structured-output schema: r=reference id, g=generated id,
    # s=semantic score, a=accident score. Explanations are intentionally
    # omitted for the full Cartesian matrix and are retained only for
    # selected matched pairs in the quality stage.
    r: str
    g: str
    s: int = Field(ge=0, le=4)
    a: int = Field(ge=0, le=2)


class PairQualityJudgeResult(BaseModel):
    r: str
    g: str
    m: int = Field(ge=0, le=2)
    p: int = Field(ge=0, le=2)
    l: int = Field(ge=0, le=2)
    e: str = Field(max_length=160)


class GeneratedSafetyJudgeResult(BaseModel):
    g: str
    u: bool
    c: bool
    e: str = Field(max_length=160)


class PairJudgeResult(BaseModel):
    reference_id: str
    generated_id: str
    semantic_match: int = Field(ge=0, le=4)
    accident_type_correctness: int = Field(ge=0, le=2)
    mitigation_appropriateness: int = Field(default=0, ge=0, le=2)
    mitigation_specificity: int = Field(default=0, ge=0, le=2)
    legal_basis_relevance: int = Field(default=0, ge=0, le=2)
    quality_evaluated: bool = True
    explanation: str = Field(max_length=160)
    quality_explanation: str | None = Field(default=None, max_length=160)


class GeneratedJudgeResult(BaseModel):
    generated_id: str
    unsupported_claim: bool
    critical_safety_error: bool
    explanation: str = Field(max_length=160)


class PairMatchBatchJudgeResult(BaseModel):
    rows: list[PairMatchJudgeResult]


class PairQualityBatchJudgeResult(BaseModel):
    rows: list[PairQualityJudgeResult]


class GeneratedBatchJudgeResult(BaseModel):
    rows: list[GeneratedSafetyJudgeResult]


class CaseJudgeResult(BaseModel):
    pair_evaluations: list[PairJudgeResult]
    generated_evaluations: list[GeneratedJudgeResult]


class RiskMatch(BaseModel):
    reference_id: str
    generated_id: str
    semantic_match: int
    accident_type_correctness: int
    mitigation_appropriateness: int
    mitigation_specificity: int
    legal_basis_relevance: int


class MetricValue(BaseModel):
    numerator: int
    denominator: int
    rate: float | None


class CaseMetrics(BaseModel):
    reference_risk_coverage: MetricValue
    unsupported_risk_rate: MetricValue
    accident_type_correctness: MetricValue
    mitigation_appropriateness: MetricValue
    mitigation_specificity: MetricValue
    legal_basis_presence: MetricValue
    legal_basis_relevance: MetricValue
    critical_safety_error_rate: MetricValue
