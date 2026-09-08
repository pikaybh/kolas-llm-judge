from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET

from .models import GeneratedRisk, ParsedRiskAssessment

ROOT_RE = re.compile(r"<risk_assessment\b[\s\S]*?</risk_assessment>", re.IGNORECASE)


def _raw_text(node: ET.Element | None) -> str | None:
    if node is None:
        return None
    value = " ".join(part.strip() for part in node.itertext() if part.strip())
    return html.unescape(re.sub(r"\s+", " ", value)).strip()


def _text(node: ET.Element | None) -> str | None:
    value = _raw_text(node)
    return None if value is None or not value or value == "-" else value


def _int(node: ET.Element | None) -> int | None:
    value = _text(node)
    if not value:
        return None
    match = re.search(r"-?\d+", value)
    return int(match.group()) if match else None


def _csv_values(node: ET.Element | None) -> list[str]:
    value = _text(node)
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip() and part.strip() != "-"]


def _accident_values(item: ET.Element) -> list[str]:
    # accident_classification is the canonical formatter output.
    # hazard_secondary_category is a broader/fallback category and may
    # contain a semicolon-joined menu of possibilities. Never append both.
    value = _text(item.find("accident_classification"))
    if not value:
        value = _text(item.find("hazard_secondary_category"))
    if not value:
        return []
    values: list[str] = []
    for part in value.split(";"):
        label = part.strip()
        if label and label != "-" and label not in values:
            values.append(label)
    return values


def extract_risk_assessment_xml(content: str) -> tuple[str, str]:
    match = ROOT_RE.search(content)
    if not match:
        raise ValueError("<risk_assessment> XML block not found")
    return match.group(0), content[match.end():].strip()


def parse_risk_assessment(content: str) -> ParsedRiskAssessment:
    xml_text, trailing = extract_risk_assessment_xml(content)
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ValueError(f"Invalid risk_assessment XML: {exc}") from exc

    method = _text(root.find("method"))
    risks: list[GeneratedRisk] = []
    for index, item in enumerate(root.findall("./items/item"), start=1):
        source_id = _text(item.find("id"))
        hazard = _text(item.find("hazard")) or _text(item.find("hazard_analysis")) or ""
        accident_values = _accident_values(item)

        mitigation_parts: list[str] = []
        for tag in ("current_safety_measures", "reduction_measures_detail"):
            value = _text(item.find(tag))
            if value and value not in mitigation_parts:
                mitigation_parts.append(value)

        post_numeric_nodes = [
            item.find("post_improvement_prob_freq"),
            item.find("post_improvement_severity"),
            item.find("post_improvement_risk_level"),
        ]
        post_numeric_present = all(node is not None for node in post_numeric_nodes)
        post_numeric_blank = post_numeric_present and all(
            not (_raw_text(node) or "") for node in post_numeric_nodes
        )
        post_verbal_node = item.find("post_improvement_risk_level_verbal")
        post_verbal_present = post_verbal_node is not None
        post_verbal_blank = post_verbal_present and not (
            _raw_text(post_verbal_node) or ""
        )

        risks.append(GeneratedRisk(
            generated_id=f"g{index:03d}",
            source_item_id=source_id,
            process=_text(item.find("hazard_primary_category")),
            subprocess=_text(item.find("risk_category")),
            hazard=hazard,
            risk_cause=_text(item.find("risk_cause")),
            accident_types=accident_values,
            likelihood=_int(item.find("prob_freq")),
            severity=_int(item.find("severity")),
            risk_score=_int(item.find("risk_level")),
            risk_level_verbal=_text(item.find("risk_level_verbal")),
            mitigation=" | ".join(mitigation_parts) if mitigation_parts else None,
            post_likelihood=_int(item.find("post_improvement_prob_freq")),
            post_severity=_int(item.find("post_improvement_severity")),
            post_risk_score=_int(item.find("post_improvement_risk_level")),
            post_risk_level_verbal=_text(item.find("post_improvement_risk_level_verbal")),
            post_improvement_numeric_tags_present=post_numeric_present,
            post_improvement_numeric_tags_blank=post_numeric_blank,
            post_improvement_verbal_tag_present=post_verbal_present,
            post_improvement_verbal_tag_blank=post_verbal_blank,
            legal_basis=_text(item.find("basis")) or _text(item.find("legal_basis_details")),
        ))

    return ParsedRiskAssessment(
        method=method,
        process_name=_text(root.find("process_name")),
        equipment=_csv_values(root.find("equipment")),
        materials=_csv_values(root.find("material")),
        risks=risks,
        xml=xml_text,
        trailing_text=trailing,
    )
