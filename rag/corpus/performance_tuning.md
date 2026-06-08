# Masking Performance Tuning for Large Tables

For large tables, run masking in batches and push simple transformations close to the database when possible. Parallelize by table or partition, but keep deterministic seeds stable so repeated values mask consistently across batches.

Tune performance by limiting sample reads, caching schema analysis, precomputing approved policy templates, and avoiding per-cell LLM calls. PII detection should run at the column level using names, types, and samples, not by scanning every row.

For weekly customer runs, store retrieval indexes and reuse them until documentation changes.

