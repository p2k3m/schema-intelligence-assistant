"""Hybrid retrieval over masking documentation.

The retriever combines a local token-vector cosine score with BM25 keyword
ranking and fuses both rankings via Reciprocal Rank Fusion. The vector stage
is intentionally deterministic for local tests; the interface can be backed by
AWS Bedrock Titan embeddings without changing the agent or generator.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path
from typing import Iterable

from ingest import DocumentChunk, load_corpus


def retrieve(
    query: str,
    pii_category_filter: str | None = None,
    top_k: int = 3,
    corpus_dir: str | Path | None = None,
) -> list[dict[str, object]]:
    index = LocalHybridIndex(load_corpus(corpus_dir))
    return index.search(
        query=query,
        metadata_filter={"pii_category": pii_category_filter} if pii_category_filter else None,
        top_k=top_k,
    )


class LocalHybridIndex:
    """In-memory retrieval backend with pre-ranking metadata filtering.

    The public `search` contract mirrors a vector database call: callers pass
    `metadata_filter` into the backend, and the backend applies it before vector
    and BM25 scoring. A production Chroma/Qdrant/Pinecone adapter would translate
    this same argument into a native `where` or filter expression.
    """

    def __init__(self, chunks: list[DocumentChunk]) -> None:
        self._chunks = chunks

    def search(
        self,
        query: str,
        metadata_filter: dict[str, str | None] | None = None,
        top_k: int = 3,
    ) -> list[dict[str, object]]:
        pii_category_filter = (metadata_filter or {}).get("pii_category")
        chunks = self._candidate_chunks(pii_category_filter)

        if not chunks:
            return []

        vector_ranking = _rank_by_vector_similarity(query, chunks)
        bm25_ranking = _rank_by_bm25(query, chunks)
        fused_scores = _reciprocal_rank_fusion(vector_ranking, bm25_ranking)
        if pii_category_filter:
            for index, chunk in enumerate(chunks):
                if chunk.pii_category == pii_category_filter:
                    fused_scores[index] = fused_scores.get(index, 0.0) + 0.02
        if re.search(r"\b(gdpr|ccpa|compliance|comply)\b", query.lower()):
            for index, chunk in enumerate(chunks):
                if chunk.source == "gdpr_ccpa_compliance.md":
                    fused_scores[index] = fused_scores.get(index, 0.0) + 0.03

        ranked = sorted(fused_scores.items(), key=lambda item: item[1], reverse=True)
        results: list[dict[str, object]] = []
        for index, score in ranked[:top_k]:
            chunk = chunks[index]
            results.append(
                {
                    "title": chunk.title,
                    "source": chunk.source,
                    "content": chunk.content,
                    "score": round(score, 6),
                    "metadata": {"pii_category": chunk.pii_category},
                    "pii_category": chunk.pii_category,
                }
            )
        return results

    def _candidate_chunks(self, pii_category_filter: str | None) -> list[DocumentChunk]:
        if not pii_category_filter:
            return list(self._chunks)
        return [
            chunk
            for chunk in self._chunks
            if chunk.pii_category in {pii_category_filter, "GENERAL"}
        ]


def _rank_by_vector_similarity(query: str, chunks: list[DocumentChunk]) -> list[int]:
    query_vector = Counter(_tokenize(query))
    doc_vectors = [Counter(_tokenize(chunk.content + " " + chunk.title)) for chunk in chunks]
    scored = [
        (index, _cosine_similarity(query_vector, doc_vector))
        for index, doc_vector in enumerate(doc_vectors)
    ]
    return [index for index, _score in sorted(scored, key=lambda item: item[1], reverse=True)]


def _rank_by_bm25(query: str, chunks: list[DocumentChunk]) -> list[int]:
    tokenized_docs = [_tokenize(chunk.content + " " + chunk.title) for chunk in chunks]
    query_terms = _tokenize(query)
    avg_doc_len = sum(len(doc) for doc in tokenized_docs) / len(tokenized_docs)
    doc_freq = _document_frequencies(tokenized_docs)
    k1 = 1.5
    b = 0.75

    scores = []
    for index, doc in enumerate(tokenized_docs):
        frequencies = Counter(doc)
        score = 0.0
        for term in query_terms:
            if frequencies[term] == 0:
                continue
            idf = math.log(1 + (len(tokenized_docs) - doc_freq[term] + 0.5) / (doc_freq[term] + 0.5))
            numerator = frequencies[term] * (k1 + 1)
            denominator = frequencies[term] + k1 * (1 - b + b * len(doc) / avg_doc_len)
            score += idf * numerator / denominator
        scores.append((index, score))

    return [index for index, _score in sorted(scores, key=lambda item: item[1], reverse=True)]


def _reciprocal_rank_fusion(*rankings: list[int], k: int = 60) -> dict[int, float]:
    fused: dict[int, float] = {}
    for ranking in rankings:
        for rank, doc_index in enumerate(ranking, start=1):
            fused[doc_index] = fused.get(doc_index, 0.0) + 1 / (k + rank)
    return fused


def _document_frequencies(tokenized_docs: Iterable[list[str]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for doc in tokenized_docs:
        counts.update(set(doc))
    return counts


def _cosine_similarity(left: Counter[str], right: Counter[str]) -> float:
    if not left or not right:
        return 0.0
    overlap = set(left) & set(right)
    numerator = sum(left[token] * right[token] for token in overlap)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    return numerator / (left_norm * right_norm)


def _tokenize(text: str) -> list[str]:
    raw_tokens = re.findall(r"[a-z0-9_]+", text.lower())
    expanded: list[str] = []
    for token in raw_tokens:
        expanded.append(token)
        expanded.extend(part for part in token.split("_") if part and part != token)
    return expanded


if __name__ == "__main__":
    for item in retrieve("how to mask email addresses", pii_category_filter="EMAIL"):
        print(f"{item['title']} [{item['source']}] score={item['score']}")
