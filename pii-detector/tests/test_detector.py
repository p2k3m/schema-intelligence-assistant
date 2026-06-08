import json
import os
import re
import subprocess
from pathlib import Path

import pytest

from detector import MASKING_FUNCTIONS, PiiDetector


detector = PiiDetector()


def test_email_column_detected():
    result = detector.detect(
        {
            "table_name": "USERS",
            "column_name": "email_address",
            "data_type": "VARCHAR(255)",
            "sample_values": ["user@example.com"],
            "nullable": True,
        }
    )
    assert result["is_pii"] is True
    assert result["pii_category"] == "EMAIL"
    assert result["recommended_masking_function"] == "EMAIL_MASK"


def test_non_pii_column_not_flagged():
    result = detector.detect(
        {
            "table_name": "ORDERS",
            "column_name": "transaction_id",
            "data_type": "BIGINT",
            "sample_values": ["100001", "100002"],
            "nullable": False,
        }
    )
    assert result["is_pii"] is False


def test_low_confidence_sets_review_required():
    result = detector.detect(
        {
            "table_name": "CONTRACTS",
            "column_name": "ref_code",
            "data_type": "VARCHAR(20)",
            "sample_values": ["C-2024-001"],
            "nullable": True,
        }
    )
    if result["confidence"] < 0.80:
        assert result["review_required"] is True
    if 0.40 <= result["confidence"] < 0.80:
        assert result["llm_escalation_recommended"] is True


def test_optional_llm_escalation_can_change_grey_zone_result():
    def reviewer(_column, preliminary):
        assert preliminary["llm_escalation_recommended"] is True
        return {
            "is_pii": True,
            "confidence": 0.86,
            "pii_category": "ACCOUNT_NUMBER",
            "reviewed_by": "mock_structured_llm",
            "reasoning": "Reference code matches customer account format in tenant-specific examples",
        }

    escalated_detector = PiiDetector(
        llm_reviewer=reviewer,
        enable_llm_escalation=True,
    )
    result = escalated_detector.detect(
        {
            "table_name": "CONTRACTS",
            "column_name": "ref_code",
            "data_type": "VARCHAR(20)",
            "sample_values": ["C-2024-001"],
            "nullable": True,
        }
    )

    assert result["llm_escalation_used"] is True
    assert result["reviewed_by"] == "mock_structured_llm"
    assert result["is_pii"] is True
    assert result["pii_category"] == "ACCOUNT_NUMBER"
    assert result["recommended_masking_function"] == "ACCOUNT_MASK"


@pytest.mark.skipif(
    os.getenv("SCHEMA_ASSISTANT_USE_OLLAMA") != "true",
    reason="Set SCHEMA_ASSISTANT_USE_OLLAMA=true to run the optional local LLM reviewer test.",
)
def test_optional_ollama_llm_escalation_path():
    def ollama_reviewer(column, preliminary):
        model = os.getenv("SCHEMA_ASSISTANT_OLLAMA_MODEL", "llama3.2:1b")
        prompt = f"""
You are reviewing a grey-zone PII detector result.
Return only JSON with keys: is_pii, confidence, pii_category, reviewed_by, reasoning.
Allowed pii_category values: FULL_NAME, EMAIL, PHONE, SSN, CREDIT_CARD, ACCOUNT_NUMBER, DATE_OF_BIRTH, ADDRESS, IP_ADDRESS, NATIONAL_ID, null.

Column descriptor:
{json.dumps(column)}

Preliminary result:
{json.dumps(preliminary)}
"""
        completed = subprocess.run(
            ["ollama", "run", model, prompt],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        match = re.search(r"\{.*\}", completed.stdout, flags=re.DOTALL)
        assert match, completed.stdout
        review = json.loads(match.group(0))
        review["reviewed_by"] = f"ollama:{model}"
        return review

    result = PiiDetector(
        llm_reviewer=ollama_reviewer,
        enable_llm_escalation=True,
    ).detect(
        {
            "table_name": "CONTRACTS",
            "column_name": "ref_code",
            "data_type": "VARCHAR(20)",
            "sample_values": ["C-2024-001"],
            "nullable": True,
        }
    )

    assert result["llm_escalation_used"] is True
    assert result["reviewed_by"].startswith("ollama:")
    assert isinstance(result["is_pii"], bool)
    assert 0.0 <= result["confidence"] <= 1.0


def test_recall_on_golden_set():
    cases = _load_cases()
    pii_cases = [case for case in cases if case["expected"]["is_pii"]]
    detected = sum(1 for case in pii_cases if detector.detect(case["input"])["is_pii"])
    recall = detected / len(pii_cases)
    assert recall >= 0.80, f"Recall {recall:.2f} below threshold"


def test_recall_on_adversarial_set():
    cases = _load_cases("adversarial_schema_test_cases.json")
    pii_cases = [case for case in cases if case["expected"]["is_pii"]]
    detected = sum(1 for case in pii_cases if detector.detect(case["input"])["is_pii"])
    recall = detected / len(pii_cases)
    assert recall >= 0.85, f"Adversarial recall {recall:.2f} below threshold"


def test_expected_categories_on_adversarial_set():
    for case in _load_cases("adversarial_schema_test_cases.json"):
        result = detector.detect(case["input"])
        expected = case["expected"]
        assert result["is_pii"] is expected["is_pii"], case["input"]["column_name"]
        if expected["is_pii"]:
            assert result["pii_category"] == expected["pii_category"], case["input"]["column_name"]
        if expected.get("review_required"):
            assert result["review_required"] is True, case["input"]["column_name"]


def test_precision_on_golden_set():
    cases = _load_cases()
    predicted_pii = [case for case in cases if detector.detect(case["input"])["is_pii"]]
    true_positives = sum(1 for case in predicted_pii if case["expected"]["is_pii"])
    precision = true_positives / len(predicted_pii)
    assert precision >= 0.75, f"Precision {precision:.2f} below threshold"


def test_expected_categories_and_masking_functions_on_golden_set():
    for case in _load_cases():
        result = detector.detect(case["input"])
        expected = case["expected"]
        assert result["is_pii"] is expected["is_pii"], case["input"]["column_name"]
        if expected["is_pii"]:
            category = expected["pii_category"]
            assert result["pii_category"] == category, case["input"]["column_name"]
            assert result["recommended_masking_function"] == MASKING_FUNCTIONS[category]
        else:
            assert result["pii_category"] is None
            assert result["recommended_masking_function"] is None


def test_golden_set_shape():
    cases = _load_cases()
    assert len(cases) >= 30
    assert sum(1 for case in cases if case["expected"]["is_pii"]) >= 15
    assert sum(1 for case in cases if not case["expected"]["is_pii"]) >= 15

    categories = {
        case["expected"]["pii_category"]
        for case in cases
        if case["expected"]["is_pii"]
    }
    assert len(categories) >= 8


def _load_cases(file_name: str = "schema_test_cases.json"):
    path = Path(__file__).with_name(file_name)
    return json.loads(path.read_text())
