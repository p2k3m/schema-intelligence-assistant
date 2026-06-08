"""Run PII detection against the generated SQLite sample database."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for relative in ("pii-detector", "masking-generator"):
    path = str(ROOT / relative)
    if path not in sys.path:
        sys.path.insert(0, path)

from build_sample_db import DEFAULT_DB_PATH, build_database
from detector import PiiDetector
from generator import MaskingConfigGenerator
from schema_sampler import sample_sqlite_schema


def main() -> None:
    db_path = build_database(DEFAULT_DB_PATH)
    schema = sample_sqlite_schema(db_path)
    detections = PiiDetector().detect_all(schema)
    config = MaskingConfigGenerator().generate(detections)
    print(json.dumps({"database": str(db_path), "detections": detections, "config": config}, indent=2))


if __name__ == "__main__":
    main()

