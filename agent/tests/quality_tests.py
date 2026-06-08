import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
for relative in ("agent", "pii-detector", "masking-generator", "rag"):
    path = str(ROOT / relative)
    if path not in sys.path:
        sys.path.insert(0, path)

import agent as agent_module
from ab_comparison import run_baseline
from agent import SchemaIntelligenceAgent
from detector import PiiDetector
from generator import MaskingConfigGenerator


agent = SchemaIntelligenceAgent()


def test_date_shift_answer_is_grounded():
    response = agent.chat("What does DATE_SHIFT do?")
    assert any(
        keyword in response.lower()
        for keyword in ["shift", "offset", "date", "preserve", "format"]
    )
    assert response_cites_source(response)


def test_doc_question_triggers_retrieval():
    fake_docs = [
        {
            "title": "EMAIL_MASK",
            "source": "email_mask.md",
            "content": "# EMAIL_MASK\n\nEMAIL_MASK protects email addresses and accepts preserve_domain.",
            "metadata": {"pii_category": "EMAIL"},
            "pii_category": "EMAIL",
            "score": 1.0,
        }
    ]
    with patch.object(agent_module, "search_masking_docs", return_value=fake_docs) as mock_search:
        response = agent.chat("What parameters does EMAIL_MASK accept?")

    mock_search.assert_called_once_with("What parameters does EMAIL_MASK accept?", "EMAIL")
    assert response_cites_source(response)
    assert semantic_overlap(response, {"email", "address", "preserve", "domain"}) >= 2


def test_out_of_scope_query_rejected():
    with patch.object(agent_module, "search_masking_docs") as mock_search, patch.object(
        agent_module, "detect_pii_columns"
    ) as mock_detect, patch.object(agent_module, "generate_masking_config") as mock_generate:
        response = agent.chat("What is the capital of France?")

    mock_search.assert_not_called()
    mock_detect.assert_not_called()
    mock_generate.assert_not_called()
    assert_no_hallucination(response)
    assert semantic_overlap(response, {"scope", "masking", "data", "schema"}) >= 2


def test_pii_detector_recall_regression():
    results = run_detector_on_golden_set()
    recall = compute_recall(results)
    assert recall >= 0.80, f"PII recall regression: {recall:.2f} < 0.80"


def test_masking_config_covers_high_confidence_detections():
    schema = load_test_schema("10_column_schema.json")
    detections = PiiDetector().detect_all(schema)
    config = MaskingConfigGenerator().generate(detections)
    high_confidence = [
        detection
        for detection in detections
        if detection["confidence"] >= 0.80 and detection["is_pii"]
    ]
    configured = {rule["column"] for rule in config["masking_rules"]}
    for detection in high_confidence:
        assert detection["column_name"] in configured


def test_ab_baseline_outputs_comparison_report():
    rows = run_baseline()
    report = Path(__file__).with_name("ab_baseline_results.md")
    assert len(rows) == 5
    assert report.exists()
    report_text = report.read_text()
    assert "Latency" in report_text
    assert "Estimated cost" in report_text


def test_agent_handles_required_interaction_types():
    schema = load_test_schema("10_column_schema.json")
    analysis = agent.chat("Analyse this schema for PII", schema=schema)
    parsed_analysis = json.loads(analysis)
    detected_columns = {item["column_name"] for item in parsed_analysis["detections"]}
    assert "email_address" in detected_columns

    detections = PiiDetector().detect_all(schema)
    config = agent.chat("Generate a masking configuration for these results", detections=detections)
    parsed_config = json.loads(config)
    assert parsed_config["masking_rules"]

    gdpr = agent.chat("How do I comply with GDPR when masking customer data?")
    assert response_cites_source(gdpr)

    single = agent.chat("Is column ref_code in table ORDERS PII?")
    assert semantic_overlap(single, {"orders", "ref_code", "confidence", "reasoning"}) >= 3

    missing = agent.chat("Mask this column: email_address")
    assert semantic_overlap(missing, {"provide", "schema", "table", "column"}) >= 2


def response_cites_source(response: str) -> bool:
    return "[Source:" in response and "]" in response


def semantic_overlap(response: str, expected_keywords: set[str]) -> int:
    normalized = response.lower().replace(".", " ").replace("_", " ")
    return sum(1 for keyword in expected_keywords if keyword.lower().replace("_", " ") in normalized)


def assert_no_hallucination(response: str) -> None:
    assert "paris" not in response.lower()
    assert "france" not in response.lower()


def run_detector_on_golden_set():
    cases = json.loads((ROOT / "pii-detector/tests/schema_test_cases.json").read_text())
    detector = PiiDetector()
    return [
        {"expected": case["expected"], "actual": detector.detect(case["input"])}
        for case in cases
    ]


def compute_recall(results) -> float:
    pii_results = [result for result in results if result["expected"]["is_pii"]]
    detected = sum(1 for result in pii_results if result["actual"]["is_pii"])
    return detected / len(pii_results)


def load_test_schema(name: str):
    return json.loads((ROOT / "masking-generator/tests" / name).read_text())
