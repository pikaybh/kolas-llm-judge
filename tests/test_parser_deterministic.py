from kolas_llm_judge.deterministic import evaluate_deterministic
from kolas_llm_judge.parser import parse_risk_assessment


VALID = '''
<risk_assessment>
  <method>빈도강도법 5x4</method>
  <industry_name>건설업</industry_name>
  <process_name>콘크리트 타설</process_name>
  <equipment>펌프카, 진동기</equipment>
  <material>콘크리트</material>
  <items>
    <item>
      <id>1</id><hazard_primary_category>콘크리트공사</hazard_primary_category>
      <hazard_secondary_category>충돌</hazard_secondary_category>
      <accident_classification>충돌</accident_classification>
      <risk_category>타설</risk_category><risk_cause>호스 휘둘림</risk_cause>
      <hazard>펌프카 호스가 휘둘려 작업자와 충돌할 위험</hazard>
      <prob_freq>3</prob_freq><severity>4</severity><risk_level>12</risk_level>
      <current_safety_measures><ul><li>접근 통제</li></ul></current_safety_measures>
      <reduction_measures_detail><ul><li>전담 신호수 배치</li></ul></reduction_measures_detail>
      <post_improvement_prob_freq>1</post_improvement_prob_freq>
      <post_improvement_severity>4</post_improvement_severity>
      <post_improvement_risk_level>4</post_improvement_risk_level>
      <basis>산업안전보건기준에 관한 규칙</basis>
    </item>
  </items>
</risk_assessment>
요약입니다.
'''


def test_parse_and_deterministic_valid() -> None:
    parsed = parse_risk_assessment(VALID)
    assert parsed.method == "빈도강도법 5x4"
    assert len(parsed.risks) == 1
    assert parsed.risks[0].risk_score == 12
    assert parsed.trailing_text == "요약입니다."
    result = evaluate_deterministic(parsed)
    assert result.item_count == 1
    assert result.schema_valid_items == 1
    assert result.checks[0].frequency_in_range is True
    assert result.checks[0].severity_in_range is True
    assert result.checks[0].score_math_correct is True
    assert result.checks[0].post_score_math_correct is True
    assert result.checks[0].post_risk_nonincreasing is True


def test_deterministic_detects_bad_numeric_values() -> None:
    parsed = parse_risk_assessment(VALID.replace("<prob_freq>3</prob_freq>", "<prob_freq>6</prob_freq>").replace("<risk_level>12</risk_level>", "<risk_level>99</risk_level>"))
    result = evaluate_deterministic(parsed)
    assert result.checks[0].frequency_in_range is False
    assert result.checks[0].score_math_correct is False


def test_deterministic_detects_increased_post_risk() -> None:
    parsed = parse_risk_assessment(
        VALID.replace(
            "<post_improvement_prob_freq>1</post_improvement_prob_freq>",
            "<post_improvement_prob_freq>4</post_improvement_prob_freq>",
        ).replace(
            "<post_improvement_risk_level>4</post_improvement_risk_level>",
            "<post_improvement_risk_level>16</post_improvement_risk_level>",
        )
    )
    result = evaluate_deterministic(parsed)
    assert result.checks[0].post_score_math_correct is True
    assert result.checks[0].post_risk_nonincreasing is False
    assert "post_risk_increased" in result.checks[0].errors


def test_verbal_method_detects_increased_post_risk() -> None:
    xml = '''
<risk_assessment>
  <method>3단계 판단법</method>
  <process_name>비계 작업</process_name>
  <items>
    <item>
      <id>1</id>
      <hazard_primary_category>가설공사</hazard_primary_category>
      <hazard_secondary_category>추락</hazard_secondary_category>
      <accident_classification>추락</accident_classification>
      <risk_category>비계 작업</risk_category>
      <risk_cause>작업발판 단부</risk_cause>
      <hazard>작업발판 단부에서 추락할 위험</hazard>
      <risk_level_verbal>중</risk_level_verbal>
      <reduction_measures_detail>안전난간 설치</reduction_measures_detail>
      <post_improvement_risk_level_verbal>상</post_improvement_risk_level_verbal>
      <basis>산업안전보건기준에 관한 규칙</basis>
    </item>
  </items>
</risk_assessment>
'''
    parsed = parse_risk_assessment(xml)
    result = evaluate_deterministic(parsed)
    assert result.checks[0].post_risk_nonincreasing is False
    assert "post_risk_increased" in result.checks[0].errors


def test_accident_classification_is_canonical_and_split() -> None:
    xml = VALID.replace(
        "<hazard_secondary_category>충돌</hazard_secondary_category>",
        "<hazard_secondary_category>감전;끼임;충돌 및 접촉</hazard_secondary_category>",
    ).replace(
        "<accident_classification>충돌</accident_classification>",
        "<accident_classification>감전;끼임</accident_classification>",
    )
    parsed = parse_risk_assessment(xml)
    assert parsed.risks[0].accident_types == ["감전", "끼임"]


def test_accident_classification_falls_back_to_secondary() -> None:
    xml = VALID.replace(
        "<hazard_secondary_category>충돌</hazard_secondary_category>",
        "<hazard_secondary_category>감전;끼임</hazard_secondary_category>",
    ).replace(
        "<accident_classification>충돌</accident_classification>",
        "",
    )
    parsed = parse_risk_assessment(xml)
    assert parsed.risks[0].accident_types == ["감전", "끼임"]


def _fast_blank_numeric_xml() -> str:
    return (
        VALID.replace(
            "<post_improvement_prob_freq>1</post_improvement_prob_freq>",
            "<post_improvement_prob_freq></post_improvement_prob_freq>",
        )
        .replace(
            "<post_improvement_severity>4</post_improvement_severity>",
            "<post_improvement_severity></post_improvement_severity>",
        )
        .replace(
            "<post_improvement_risk_level>4</post_improvement_risk_level>",
            "<post_improvement_risk_level></post_improvement_risk_level>",
        )
    )


def test_fast_contract_accepts_present_blank_post_tags() -> None:
    parsed = parse_risk_assessment(_fast_blank_numeric_xml())
    risk = parsed.risks[0]
    assert risk.post_improvement_numeric_tags_present is True
    assert risk.post_improvement_numeric_tags_blank is True

    result = evaluate_deterministic(
        parsed,
        post_improvement_mode="blank",
    )
    assert result.post_improvement_mode == "blank"
    assert result.schema_valid_items == 1
    assert result.checks[0].post_frequency_in_range is None
    assert result.checks[0].post_severity_in_range is None
    assert result.checks[0].post_score_math_correct is None
    assert result.checks[0].post_risk_nonincreasing is None
    assert result.checks[0].errors == []


def test_required_contract_rejects_blank_post_tags() -> None:
    parsed = parse_risk_assessment(_fast_blank_numeric_xml())
    result = evaluate_deterministic(
        parsed,
        post_improvement_mode="required",
    )
    assert result.schema_valid_items == 0
    assert "missing_post_frequency" in result.checks[0].errors
    assert "missing_post_severity" in result.checks[0].errors
    assert "missing_post_risk_score" in result.checks[0].errors


def test_fast_contract_rejects_nonblank_or_missing_post_tags() -> None:
    nonblank = parse_risk_assessment(VALID)
    result = evaluate_deterministic(
        nonblank,
        post_improvement_mode="blank",
    )
    assert result.schema_valid_items == 0
    assert (
        "post_improvement_numeric_tags_not_blank"
        in result.checks[0].errors
    )

    missing_xml = _fast_blank_numeric_xml().replace(
        "<post_improvement_risk_level></post_improvement_risk_level>",
        "",
    )
    missing = parse_risk_assessment(missing_xml)
    result = evaluate_deterministic(
        missing,
        post_improvement_mode="blank",
    )
    assert result.schema_valid_items == 0
    assert (
        "missing_post_improvement_numeric_tags"
        in result.checks[0].errors
    )


def test_fast_verbal_contract_requires_present_blank_post_tag() -> None:
    xml = '''
<risk_assessment>
  <method>3단계 판단법</method>
  <items>
    <item>
      <id>1</id>
      <accident_classification>추락</accident_classification>
      <hazard_analysis>발판 단부 추락 위험</hazard_analysis>
      <hazard>발판 단부 추락 위험</hazard>
      <risk_level_verbal>중</risk_level_verbal>
      <reduction_measures_detail>안전난간 설치</reduction_measures_detail>
      <post_improvement_risk_level_verbal></post_improvement_risk_level_verbal>
      <basis>산업안전보건기준에 관한 규칙</basis>
    </item>
  </items>
</risk_assessment>
'''
    parsed = parse_risk_assessment(xml)
    assert parsed.risks[0].post_improvement_verbal_tag_present is True
    assert parsed.risks[0].post_improvement_verbal_tag_blank is True
    result = evaluate_deterministic(
        parsed,
        post_improvement_mode="blank",
    )
    assert result.schema_valid_items == 1
    assert result.checks[0].post_risk_nonincreasing is None
