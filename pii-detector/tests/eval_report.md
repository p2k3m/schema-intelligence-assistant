# PII Detector Evaluation Report

Golden set: `pii-detector/tests/schema_test_cases.json`

- Total cases: 30
- PII cases: 15
- Non-PII cases: 15
- True positives: 15
- False positives: 0
- False negatives: 0
- Precision: 1.00
- Recall@PII: 1.00

The Day 1 success metric in `QUALITY_CRITERIA.md` requires Recall@PII >= 0.80. The current detector meets that threshold on the labelled golden set.

