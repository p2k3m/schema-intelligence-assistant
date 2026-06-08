from pathlib import Path

from generator import DetectionResult, MaskingConfigGenerator


generator = MaskingConfigGenerator()


def test_low_confidence_goes_to_review_queue():
    detections = [
        DetectionResult(
            column="ref_code",
            table="ORDERS",
            is_pii=True,
            confidence=0.62,
            pii_category="ACCOUNT_NUMBER",
            recommended_masking_function="ACCOUNT_MASK",
            review_required=True,
        )
    ]
    config = generator.generate(detections)
    assert any(rule["column"] == "ref_code" for rule in config["review_queue"])
    assert not any(rule["column"] == "ref_code" for rule in config["masking_rules"])


def test_documentation_references_exist():
    config = generator.generate(sample_detections())
    corpus_files = {path.name for path in Path("rag/corpus").glob("*.md")}
    for rule in config["masking_rules"]:
        doc_file = rule["documentation_reference"].split("#")[0]
        assert doc_file in corpus_files


def test_summary_counts_all_detection_buckets():
    config = generator.generate(sample_detections())
    assert config["confidence_summary"]["auto_configured"] == 2
    assert config["confidence_summary"]["requires_review"] == 1
    assert config["confidence_summary"]["not_pii"] == 1


def sample_detections():
    return [
        DetectionResult(
            column="email_address",
            table="USERS",
            is_pii=True,
            confidence=0.94,
            pii_category="EMAIL",
            recommended_masking_function="EMAIL_MASK",
        ),
        DetectionResult(
            column="dob",
            table="PATIENTS",
            is_pii=True,
            confidence=0.91,
            pii_category="DATE_OF_BIRTH",
            recommended_masking_function="DATE_SHIFT",
        ),
        DetectionResult(
            column="ref_code",
            table="ORDERS",
            is_pii=True,
            confidence=0.62,
            pii_category="ACCOUNT_NUMBER",
            recommended_masking_function="ACCOUNT_MASK",
            review_required=True,
        ),
        DetectionResult(
            column="transaction_id",
            table="ORDERS",
            is_pii=False,
            confidence=0.18,
            pii_category=None,
        ),
    ]

