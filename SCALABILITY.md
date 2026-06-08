# Scalability

## PII Detection at Scale

For a 5,000-column schema, keep detection under 30 seconds by scoring columns independently with deterministic name, type, and sample-value signals. Avoid per-row scans and avoid LLM calls per column. Batch sample profiling, cache normalized identifiers, and parallelize by table. High-confidence local matches should cover about 80 percent of columns with zero API cost. Only grey-zone columns, currently confidence 0.40 to 0.80, should be batched for embedding or LLM review.

## RAG Freshness

Documentation should be indexed from the product documentation repository on every merge to the docs main branch. A CI job can rebuild chunks, metadata, BM25 statistics, and vector embeddings, then publish a versioned retrieval index. Each answer should cite the source file and index version so stale answers are traceable.

The local retriever reports vector-only, BM25-only, and hybrid Recall@3 so a production team can see whether embedding changes improve quality. The hybrid path remains the release gate because it protects exact function-name queries and broader semantic questions.

## Cost Control

The submitted local path has zero LLM API cost. For a production estimate, assume 500 customers run 5,000-column schemas weekly: about 10 million columns per month. If 80 percent are handled locally and the remaining 20 percent are batched into 50-column review prompts, that is about 40,000 prompts per month. With an example `gpt-4o-mini` price assumption of $0.15 per million input tokens and $0.60 per million output tokens, and each 50-column batch using about 2,200 input tokens and 900 output tokens, cost is about $0.0035 per 1,000 columns or about $35 per month for the full workload. Further optimization comes from caching column-pattern decisions, using async batch APIs, and retraining pattern rules from reviewer feedback.

## Quality Monitoring

Alert on PII recall below 95 percent on adjudicated samples, false-negative incidents above zero for regulated categories, review queue rate above 35 percent, high-confidence rule rejection above 20 percent, RAG Recall@3 below 0.70, documentation answers without citations above zero, and out-of-scope refusal failures above zero.
