# Configuring and Running a Masking Job

A masking job defines a source connection, target connection, table selection, masking rules, execution schedule, and validation policy. Each masking rule includes the table, column, function, parameters, confidence, and review state.

Recommended workflow:

1. Import or inspect the schema.
2. Detect PII columns and review low-confidence results.
3. Generate masking rules for approved detections.
4. Run a dry run to validate row counts and data types.
5. Execute the job and review audit output.

Jobs should fail closed when a configured masking function is missing or a column type is incompatible.

