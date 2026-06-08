import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from ingest import load_corpus
from retrieve import LocalHybridIndex, retrieve


def test_retrieval_supports_category_filter():
    results = retrieve("how to mask email addresses", pii_category_filter="EMAIL", top_k=3)
    assert results
    assert all(result["metadata"]["pii_category"] in {"EMAIL", "GENERAL"} for result in results)
    assert results[0]["source"] == "email_mask.md"


def test_category_filter_is_passed_to_retrieval_backend():
    calls = []
    original_search = LocalHybridIndex.search

    def spy_search(self, *args, **kwargs):
        calls.append(kwargs)
        return original_search(self, *args, **kwargs)

    with patch.object(LocalHybridIndex, "search", spy_search):
        retrieve("how to mask email addresses", pii_category_filter="EMAIL", top_k=3)

    assert calls[0]["metadata_filter"] == {"pii_category": "EMAIL"}


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


def test_vector_bm25_and_hybrid_modes_are_available():
    for mode in ("vector", "bm25", "hybrid"):
        results = retrieve("what does DATE_SHIFT do", top_k=3, mode=mode)
        assert results
        assert all("score" in result for result in results)


@pytest.mark.skipif(
    os.getenv("SCHEMA_ASSISTANT_TEST_SENTENCE_TRANSFORMERS") != "true",
    reason="Set SCHEMA_ASSISTANT_TEST_SENTENCE_TRANSFORMERS=true to verify the optional sentence-transformers backend.",
)
def test_optional_sentence_transformers_backend(monkeypatch):
    monkeypatch.setenv("SCHEMA_ASSISTANT_EMBEDDING_BACKEND", "sentence-transformers")
    index = LocalHybridIndex(load_corpus())
    if not index.embedding_backend_name.startswith("sentence-transformers/"):
        pytest.skip("sentence-transformers backend is unavailable; deterministic TF-IDF fallback is active.")

    results = index.search("what does DATE_SHIFT do", top_k=3, mode="vector")
    assert index.embedding_backend_name == "sentence-transformers/all-MiniLM-L6-v2"
    assert results
