Implementation: Python

# Schema Intelligence Assistant

AI-assisted schema review for enterprise data masking. The project detects likely PII columns, recommends masking functions, retrieves masking documentation with hybrid RAG, generates masking configuration JSON, and exposes a local agent runner.

## Architecture

```text
                 +--------------------+
Schema JSON ---> | PII Detector       |
                 | - aliases          |
                 | - regex samples    |
                 | - confidence bands |
                 +---------+----------+
                           |
                           v
                 +--------------------+
                 | Detection Results  |
                 | PII / Review / No  |
                 +---------+----------+
                           |
                           v
                 +--------------------+        +----------------------+
                 | Masking Generator  | <----> | RAG Retriever         |
                 | rules + review q   |        | Vector + BM25 + RRF   |
                 +---------+----------+        +----------+-----------+
                           |                              |
                           v                              v
                 +--------------------+        +----------------------+
                 | Masking Config JSON|        | Cited doc snippets    |
                 +--------------------+        +----------------------+

                 Agent orchestrates all tools and refuses out-of-scope input.
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run Locally

```bash
python3 app.py --demo
python3 app.py --question "What does DATE_SHIFT do and what parameters does it accept?"
python3 app.py --question "Analyse this schema for PII" --schema masking-generator/tests/10_column_schema.json
python3 database/run_db_analysis.py
uvicorn api:app --reload
```

The default implementation runs locally without cloud credentials. `.env.example` documents the AWS Bedrock settings I would use when replacing the deterministic local vector stage or uncertain-column review path with AWS-hosted embeddings or model calls. Real AWS keys must stay in the AWS credential chain, never in git.

## Test

```bash
python3 -m pytest -q
python3 rag/eval/evaluate_retrieval.py
python3 agent/tests/ab_comparison.py
```

Optional local model checks:

```bash
SCHEMA_ASSISTANT_USE_OLLAMA=true python3 -m pytest pii-detector/tests/test_detector.py -q
SCHEMA_ASSISTANT_TEST_SENTENCE_TRANSFORMERS=true SCHEMA_ASSISTANT_EMBEDDING_BACKEND=sentence-transformers python3 -m pytest rag/eval/test_retrieval.py -q
SCHEMA_ASSISTANT_AB_USE_OLLAMA=true python3 agent/tests/ab_comparison.py
```

## Approach

The detector uses a hybrid deterministic signal scorer: semantic column/table-name patterns plus sample-value pattern checks. This gives repeatable test results, no API dependency, and low per-column cost for onboarding-scale schemas. In a production version, columns with uncertain confidence would be routed to an embedding or LLM review stage rather than calling an LLM for every column.

## Design Decisions

- Python was chosen because the task rewards fast iteration on AI quality tests, RAG evaluation, and lightweight local tooling.
- The Day 1 detector is deterministic so recall, precision, and review routing can be regression tested without network or model variance.
- The RAG retriever uses hybrid vector cosine plus BM25 with Reciprocal Rank Fusion because exact masking-function names and semantic context both matter.
- The vector leg uses local TF-IDF embeddings by default for deterministic CI; `SCHEMA_ASSISTANT_EMBEDDING_BACKEND=sentence-transformers` can switch to local `all-MiniLM-L6-v2` embeddings when that optional runtime is available.
- Every retrieved chunk carries `pii_category` metadata so documentation answers and masking-rule references can be category-filtered.
- The local agent uses a LangGraph `StateGraph` with explicit route state and conditional edges; documentation answers must call retrieval before synthesis, and out-of-scope routes end before tool use.
- The LangGraph graph plus optional `llm_reviewer` hook implements the task's recommended hybrid approach: cheap deterministic handling for confident cases, model review only for uncertain columns.
- AWS is treated as the production extension point, not a required local dependency, so reviewers can run the submission without secrets.
- The `database/` demo builds and samples a real SQLite schema so the same detector contract can later sit behind live enterprise database connectors.
- A minimal FastAPI wrapper exposes the same agent as `/chat` and `/analyze`, demonstrating how the local workflow can become a service endpoint.

## What I Would Do Differently With More Time

- Add a larger labelled schema corpus from real anonymized customer patterns.
- Add AWS Bedrock Titan embeddings behind the same `retrieve()` interface and compare Recall@3 against the local vector baseline.
- Add a human feedback store so review decisions improve future thresholds.
- Add policy profiles for different industries and geographies.
- Package the local runner as a small FastAPI service for UI and API demos.
- Replace the SQLite demo adapter with read-only connectors for PostgreSQL, Oracle, SQL Server, and Snowflake metadata APIs.

## Known Limitations

| Limitation | Current Guardrail | Future Fix |
|---|---|---|
| Obfuscated customer-specific PII names may be missed | Review queue + optional LLM reviewer | Add feedback-driven alias expansion |
| Sample-only PII can be under-scored | Strong regex sample signals and adversarial tests | Add sampled-value embeddings and customer policy profiles |
| RAG corpus is local markdown | Versioned corpus files + Recall@3 eval gate | Docs CI ingestion pipeline |
| Agent routing is deterministic | LangGraph state tests for required routes and synonyms | Add an intent classifier with an intent eval set |
| Live model checks are optional | Env-gated Ollama and sentence-transformers tests | Run optional checks in a nightly model-enabled workflow |

## Test Coverage Summary

Covered:

- PII detector unit tests, exact category mapping, recall, precision, and dataset shape.
- Golden set with 38 labelled cases across at least 8 PII categories.
- Adversarial set with 30 realistic alias, sample-only, and false-positive trap cases.
- RAG category filtering and Recall@3.
- Masking generator review queue behavior, documentation references, and detector-to-generator integration.
- Agent semantic correctness, retrieval grounding enforcement, out-of-scope rejection, PII recall regression, masking config completeness, and A/B baseline report generation.
- Two `@pytest.mark.skipif` tests cover real local-model paths when enabled: `SCHEMA_ASSISTANT_USE_OLLAMA=true` for grey-zone LLM review, and `SCHEMA_ASSISTANT_TEST_SENTENCE_TRANSFORMERS=true` with `SCHEMA_ASSISTANT_EMBEDDING_BACKEND=sentence-transformers` for embedding retrieval.

Not covered:

- Production database connectivity, because the assignment is self-contained; the SQLite demo proves the schema-sampling contract with a real local database.
- Live AWS Bedrock calls, because tests should run without credentials and no secrets should be committed.
- UI workflows, because the requested deliverable is a standalone engineering tool.
