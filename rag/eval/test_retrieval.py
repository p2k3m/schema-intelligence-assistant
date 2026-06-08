import json
from pathlib import Path

from retrieve import retrieve


def test_retrieval_supports_category_filter():
    results = retrieve("how to mask email addresses", pii_category_filter="EMAIL", top_k=3)
    assert results
    assert all(result["metadata"]["pii_category"] in {"EMAIL", "GENERAL"} for result in results)
    assert results[0]["source"] == "email_mask.md"


def test_recall_at_3_on_masking_queries():
    queries = json.loads(Path(__file__).with_name("masking_queries.json").read_text())
    hits = 0
    for item in queries:
        results = retrieve(item["query"], top_k=3)
        titles = {result["title"] for result in results}
        if item["expected_source_title"] in titles:
            hits += 1

    recall_at_3 = hits / len(queries)
    assert recall_at_3 >= 0.70, f"Recall@3 {recall_at_3:.2f} below threshold"

