import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for relative in ("agent", "pii-detector", "masking-generator", "rag"):
    path = str(ROOT / relative)
    if path not in sys.path:
        sys.path.insert(0, path)

from ab_comparison import run_baseline
from agent import SchemaIntelligenceAgent
from detector import PiiDetector
from generator import MaskingConfigGenerator
from tools import tool_call_tracker


agent = SchemaIntelligenceAgent()


def test_date_shift_answer_is_grounded():
    response = agent.chat("What does DATE_SHIFT do?")
    assert any(
        keyword in response.lower()
        for keyword in ["shift", "offset", "date", "preserve", "format"]
    )
    assert response_cites_source(response)


def test_doc_question_triggers_retrieval():
    with tool_call_tracker() as tracker:
        agent.chat("What parameters does EMAIL_MASK accept?")
    assert "search_masking_docs" in tracker.called_tools


def test_out_of_scope_query_rejected():
    response = agent.chat("What is the capital of France?")
    assert_no_hallucination(response)
    assert any(
        phrase in response.lower()
        for phrase in ["out of scope", "can't help", "masking", "data"]
    )


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
    assert "Baseline A" in report.read_text()


def test_agent_handles_required_interaction_types():
    schema = load_test_schema("10_column_schema.json")
    analysis = agent.chat("Analyse this schema for PII", schema=schema)
    assert "email_address" in analysis

    detections = PiiDetector().detect_all(schema)
    config = agent.chat("Generate a masking configuration for these results", detections=detections)
    assert "masking_rules" in config

    gdpr = agent.chat("How do I comply with GDPR when masking customer data?")
    assert response_cites_source(gdpr)

    single = agent.chat("Is column ref_code in table ORDERS PII?")
    assert "ORDERS.ref_code" in single

    missing = agent.chat("Mask this column: email_address")
    assert "provide" in missing.lower() and "schema" in missing.lower()


def response_cites_source(response: str) -> bool:
    return "[Source:" in response and "]" in response


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

