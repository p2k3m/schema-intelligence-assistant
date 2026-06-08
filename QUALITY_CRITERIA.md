# Quality Criteria

## Detection Thresholds

PII detection has asymmetric risk. Missing PII can create a compliance incident, while a false positive usually adds review work or an unnecessary masking recommendation. The Day 1 detector therefore optimizes for recall before precision.

- Minimum shippable Recall@PII: 0.80 on the golden labelled set.
- Target Recall@PII for production hardening: 0.95 or higher before automatic policy generation.
- Minimum precision target for Day 1: 0.75 on the golden labelled set.
- Production precision target: 0.85 or higher after adding more customer-like schemas.

Confidence bands:

- `confidence >= 0.80`: auto-tag the column and recommend the mapped masking function.
- `0.60 <= confidence < 0.80`: tag as probable PII but require human review.
- `0.35 <= confidence < 0.60`: do not auto-tag; route to human review when generic identifier signals exist.
- `confidence < 0.35`: treat as non-PII unless a downstream reviewer or customer policy says otherwise.

Production escalation policy:

- `0.40 <= confidence < 0.80`: route to batched LLM or embedding-assisted review only after cheap local rules have run.
- `confidence >= 0.80` and `confidence < 0.40`: avoid LLM calls by default to control cost and latency.

The chosen implementation starts with a deterministic hybrid scorer because it is recall-first, low-cost, and regression-testable. It uses semantic column patterns, table context, data type hints, and sample-value regex checks before any optional model escalation. This keeps the 5,000-column case fast while preserving an upgrade path for ambiguous columns.

## Test Data Plan

The labelled dataset is stored in `pii-detector/tests/schema_test_cases.json`. Each test case contains:

- `table_name`
- `column_name`
- `data_type`
- `sample_values`
- `nullable`
- expected `is_pii`
- expected `pii_category` where applicable

The initial golden set has 30 column descriptors: 15 PII and 15 non-PII. It covers at least eight required PII categories and deliberately includes examples that are easy to misclassify.

Required edge cases:

- Obfuscated or abbreviated column names, such as `cust_acct_no` and `msisdn`.
- Obfuscated identifiers such as `usr_ssn_txt` and `nat_ins_no`, where sample values should reinforce the classification.
- Non-English names, such as `correo_electronico`.
- Numeric PII that must be distinguished from business identifiers, such as SSN versus `transaction_id`.
- Unusual regional identifiers, such as `national_insurance_number`.
- Non-PII fields containing tempting tokens, such as `card_type`, `email_template_name`, and `account_status`.
- Values that are masked, null-like, or partial, such as `****1234`.

## Day 1 Success Metric

The implementation is considered Day 1 shippable only if it reaches at least `Recall@PII >= 0.80` on the golden set. The test suite also checks precision so the detector cannot pass by flagging everything as PII.
