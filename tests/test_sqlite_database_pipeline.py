import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for relative in ("database", "pii-detector", "masking-generator"):
    path = str(ROOT / relative)
    if path not in sys.path:
        sys.path.insert(0, path)

from build_sample_db import build_database
from detector import PiiDetector
from generator import MaskingConfigGenerator
from schema_sampler import sample_sqlite_schema


def test_sqlite_database_pipeline_detects_pii_and_generates_rules(tmp_path):
    db_path = build_database(tmp_path / "sample_customer.db")
    schema = sample_sqlite_schema(db_path)
    detections = PiiDetector().detect_all(schema)
    config = MaskingConfigGenerator().generate(detections)

    detected_by_column = {
        detection["column_name"]: detection
        for detection in detections
        if detection["is_pii"]
    }
    for column in (
        "full_name",
        "email_address",
        "mobile_phone",
        "date_of_birth",
        "shipping_address",
        "cust_acct_no",
        "credit_card_number",
        "last_login_ip",
        "national_insurance_number",
    ):
        assert column in detected_by_column

    non_pii_columns = {
        detection["column_name"]
        for detection in detections
        if not detection["is_pii"]
    }
    assert "transaction_id" in non_pii_columns
    assert "account_status" in non_pii_columns

    configured_columns = {rule["column"] for rule in config["masking_rules"]}
    assert "email_address" in configured_columns
    assert "credit_card_number" in configured_columns
    assert "transaction_id" not in configured_columns
