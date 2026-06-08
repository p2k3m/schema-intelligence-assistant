"""Hybrid retrieval over masking documentation.

The retriever combines vector similarity with BM25 keyword ranking and fuses
both rankings via Reciprocal Rank Fusion. The default vector stage is a local
TF-IDF embedding so CI stays deterministic; setting
`SCHEMA_ASSISTANT_EMBEDDING_BACKEND=sentence-transformers` attempts to use
`all-MiniLM-L6-v2` embeddings when that optional local dependency is healthy.
"""

from __future__ import annotations

import math
import os
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
    mode: str = "hybrid",
) -> list[dict[str, object]]:
    index = LocalHybridIndex(load_corpus(corpus_dir))
    return index.search(
        query=query,
        metadata_filter={"pii_category": pii_category_filter} if pii_category_filter else None,
        top_k=top_k,
        mode=mode,
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
        self._embedding_backend = _EmbeddingBackend(chunks)

    def search(
        self,
        query: str,
        metadata_filter: dict[str, str | None] | None = None,
        top_k: int = 3,
        mode: str = "hybrid",
    ) -> list[dict[str, object]]:
        pii_category_filter = (metadata_filter or {}).get("pii_category")
        chunks = self._candidate_chunks(pii_category_filter)

        if not chunks:
            return []

        vector_ranking = self._rank_by_vector_similarity(query, chunks)
        bm25_ranking = _rank_by_bm25(query, chunks)
        if mode == "vector":
            fused_scores = _ranking_to_scores(vector_ranking)
        elif mode == "bm25":
            fused_scores = _ranking_to_scores(bm25_ranking)
        elif mode == "hybrid":
            fused_scores = _reciprocal_rank_fusion(vector_ranking, bm25_ranking)
        else:
            raise ValueError(f"Unsupported retrieval mode: {mode}")

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

    def _rank_by_vector_similarity(self, query: str, chunks: list[DocumentChunk]) -> list[int]:
        return self._embedding_backend.rank(query, chunks)


class _EmbeddingBackend:
    def __init__(self, chunks: list[DocumentChunk]) -> None:
        self._all_chunks = chunks
        self.name = "tfidf"
        self._model = None
        self._vocabulary: dict[str, int] = {}
        self._idf: dict[str, float] = {}
        self._vectors_by_source_key: dict[tuple[str, str], list[float]] = {}

        if os.getenv("SCHEMA_ASSISTANT_EMBEDDING_BACKEND") == "sentence-transformers":
            self._model = self._try_sentence_transformer()
        if self._model:
            self.name = "sentence-transformers/all-MiniLM-L6-v2"
            self._vectors_by_source_key = {
                _chunk_key(chunk): vector
                for chunk, vector in zip(chunks, self._model.encode(_chunk_text(chunk)).tolist())
            }
        else:
            self._build_tfidf_vectors(chunks)

    def rank(self, query: str, chunks: list[DocumentChunk]) -> list[int]:
        query_vector = self._embed_query(query)
        scored = [
            (index, _dense_cosine_similarity(query_vector, self._vectors_by_source_key[_chunk_key(chunk)]))
            for index, chunk in enumerate(chunks)
        ]
        return [index for index, _score in sorted(scored, key=lambda item: item[1], reverse=True)]

    def _try_sentence_transformer(self):
        try:
            from sentence_transformers import SentenceTransformer

            return SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        except Exception:
            return None

    def _build_tfidf_vectors(self, chunks: list[DocumentChunk]) -> None:
        tokenized_docs = [_tokenize(_chunk_text(chunk)) for chunk in chunks]
        doc_freq = _document_frequencies(tokenized_docs)
        total_docs = len(tokenized_docs)
        terms = sorted(doc_freq)
        self._vocabulary = {term: index for index, term in enumerate(terms)}
        self._idf = {
            term: math.log((1 + total_docs) / (1 + doc_freq[term])) + 1
            for term in terms
        }
        self._vectors_by_source_key = {
            _chunk_key(chunk): self._tfidf_vector(tokens)
            for chunk, tokens in zip(chunks, tokenized_docs)
        }

    def _embed_query(self, query: str) -> list[float]:
        if self._model:
            return self._model.encode([query]).tolist()[0]
        return self._tfidf_vector(_tokenize(query))

    def _tfidf_vector(self, tokens: list[str]) -> list[float]:
        frequencies = Counter(tokens)
        vector = [0.0] * len(self._vocabulary)
        for term, frequency in frequencies.items():
            index = self._vocabulary.get(term)
            if index is not None:
                vector[index] = frequency * self._idf[term]
        return vector


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


def _ranking_to_scores(ranking: list[int]) -> dict[int, float]:
    return {doc_index: 1 / rank for rank, doc_index in enumerate(ranking, start=1)}


def _document_frequencies(tokenized_docs: Iterable[list[str]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for doc in tokenized_docs:
        counts.update(set(doc))
    return counts


def _dense_cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    numerator = sum(left_value * right_value for left_value, right_value in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def _tokenize(text: str) -> list[str]:
    raw_tokens = re.findall(r"[a-z0-9_]+", text.lower())
    expanded: list[str] = []
    for token in raw_tokens:
        expanded.append(token)
        expanded.extend(part for part in token.split("_") if part and part != token)
    return expanded


def _chunk_text(chunk: DocumentChunk) -> str:
    return f"{chunk.title}\n{chunk.content}"


def _chunk_key(chunk: DocumentChunk) -> tuple[str, str]:
    return (chunk.source, chunk.pii_category)


if __name__ == "__main__":
    for item in retrieve("how to mask email addresses", pii_category_filter="EMAIL"):
        print(f"{item['title']} [{item['source']}] score={item['score']}")
