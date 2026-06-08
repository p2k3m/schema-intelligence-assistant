# Common Masking Errors and Troubleshooting

Common masking errors include incompatible data types, generated values that exceed column length, unsupported locale configuration, missing deterministic seeds, and policies that preserve too many original characters.

If a masking job fails, inspect the rule-level error first. Confirm that the selected masking function matches the detected PII category. For example, `EMAIL_MASK` expects an email-like string, while `DATE_SHIFT` expects a date or timestamp.

For low-confidence detections, route the column to human review instead of forcing a masking rule automatically.

