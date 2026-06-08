# Scalability

## PII Detection at Scale

For a 5,000-column schema, keep detection under 30 seconds by scoring columns independently with deterministic name, type, and sample-value signals. Avoid per-row scans and avoid LLM calls per column. Batch sample profiling, cache normalized identifiers, and parallelize by table. Only uncertain columns should be routed to a slower embedding or LLM review stage.

## RAG Freshness

Documentation should be indexed from the product documentation repository on every merge to the docs main branch. A CI job can rebuild chunks, metadata, BM25 statistics, and vector embeddings, then publish a versioned retrieval index. Each answer should cite the source file and index version so stale answers are traceable.

## Cost Control

The submitted local path has zero LLM API cost. If AWS Bedrock is added for uncertain-column review and doc embeddings, cost stays low by using deterministic detection for high-confidence cases, caching embeddings, and calling the model only for review-bound columns. At 500 customers running weekly, if 5,000 columns are scored locally and only 5 percent need LLM review, that is about 500,000 review prompts per month. Optimization should focus on prompt batching, smaller models, and active learning that reduces review volume.

## Quality Monitoring

Alert on PII recall below 95 percent on adjudicated samples, false-negative incidents above zero for regulated categories, review queue rate above 35 percent, high-confidence rule rejection above 20 percent, RAG Recall@3 below 0.70, documentation answers without citations above zero, and out-of-scope refusal failures above zero.

