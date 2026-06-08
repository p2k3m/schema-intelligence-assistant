import json
from pathlib import Path

from detector import PiiDetector
from generator import MaskingConfigGenerator


def test_detector_to_generator_pipeline_covers_high_confidence_detections():
    schema = json.loads(Path(__file__).with_name("10_column_schema.json").read_text())
    detections = PiiDetector().detect_all(schema)
    config = MaskingConfigGenerator().generate(detections)

    high_confidence = [
        detection
        for detection in detections
        if detection["is_pii"] and detection["confidence"] >= 0.80
    ]
    configured = {rule["column"] for rule in config["masking_rules"]}
    for detection in high_confidence:
        assert detection["column_name"] in configured


def test_pipeline_leaves_non_pii_out_of_masking_rules():
    schema = json.loads(Path(__file__).with_name("10_column_schema.json").read_text())
    detections = PiiDetector().detect_all(schema)
    config = MaskingConfigGenerator().generate(detections)

    non_pii_columns = {
        detection["column_name"] for detection in detections if not detection["is_pii"]
    }
    configured = {rule["column"] for rule in config["masking_rules"]}
    assert configured.isdisjoint(non_pii_columns)

