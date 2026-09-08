from __future__ import annotations

import pandas as pd

from kolas_llm_judge.dataset import build_scenarios


def test_build_scenarios_groups_without_reference_leakage() -> None:
    df = pd.DataFrame([
        {"공정": "콘크리트작업", "세부공정": "타설", "설비": "펌프카", "물질": "콘크리트", "유해위험요인": "호스 휘둘림", "사고분류": "충돌 및 접촉", "위험 가능성": "중(2)", "위험 중대성": "중(2)", "위험성": "보통(4)", "감소대책": "호스 통제", "관련근거(법규)": "제1조"},
        {"공정": "콘크리트작업", "세부공정": "타설", "설비": "진동기", "물질": "", "유해위험요인": "누전", "사고분류": "감전", "위험 가능성": "하(1)", "위험 중대성": "중(2)", "위험성": "낮음(2)", "감소대책": "누전차단기", "관련근거(법규)": "제2조"},
    ])
    scenario = build_scenarios(df)[0]
    assert len(scenario.references) == 2
    assert scenario.input.equipment == ["펌프카", "진동기"]
    payload = scenario.input.model_dump()
    assert "유해위험요인" not in payload
    assert "감소대책" not in payload


def test_score_parsing() -> None:
    df = pd.DataFrame([{"공정": "전기", "세부공정": None, "설비": None, "물질": None, "유해위험요인": "누전", "사고분류": "감전;화상", "위험 가능성": "하\n(1)", "위험 중대성": "상(4)", "위험성": "4", "감소대책": None, "관련근거(법규)": None}])
    ref = build_scenarios(df)[0].references[0]
    assert ref.likelihood == 1
    assert ref.severity == 4
    assert ref.risk_score == 4
    assert ref.accident_types == ["감전", "화상"]
