from kolas_llm_judge.models import EvaluationScenario, ScenarioInput
from kolas_llm_judge.sut_client import build_sut_message


def test_sut_message_contains_only_input_context() -> None:
    scenario = EvaluationScenario(
        case_id="case-test",
        source_rows=[2],
        input=ScenarioInput(process="철근공사", subprocess="조립", equipment=["절단기"], materials=["철근"]),
        references=[],
    )
    message = build_sut_message(scenario)
    assert "철근공사" in message and "조립" in message and "절단기" in message
    assert "유해위험요인" not in message
    assert "감소대책" not in message
