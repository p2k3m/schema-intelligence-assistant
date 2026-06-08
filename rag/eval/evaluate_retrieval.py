import json
import time
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from retrieve import retrieve


def main() -> None:
    query_path = Path(__file__).with_name("masking_queries.json")
    report_path = Path(__file__).with_name("recall_report.md")
    queries = json.loads(query_path.read_text())
    modes = ("vector", "bm25", "hybrid")
    mode_rows = {mode: [] for mode in modes}
    mode_hits = {mode: 0 for mode in modes}
    mode_latency_ms = {mode: 0.0 for mode in modes}

    for item in queries:
        for mode in modes:
            started = time.perf_counter()
            results = retrieve(item["query"], top_k=3, mode=mode)
            mode_latency_ms[mode] += (time.perf_counter() - started) * 1000
            titles = [result["title"] for result in results]
            hit = item["expected_source_title"] in titles
            mode_hits[mode] += int(hit)
            mode_rows[mode].append((item["query"], item["expected_source_title"], titles, hit))

    hybrid_recall = mode_hits["hybrid"] / len(queries)
    lines = [
        "# RAG Recall Report",
        "",
        f"Hybrid Recall@3: {hybrid_recall:.2f} ({mode_hits['hybrid']}/{len(queries)})",
        "",
        "| Retriever | Recall@3 | Total latency ms | Avg latency ms/query |",
        "|---|---:|---:|---:|",
    ]
    for mode in modes:
        recall = mode_hits[mode] / len(queries)
        total_latency = mode_latency_ms[mode]
        lines.append(
            f"| {mode} | {recall:.2f} ({mode_hits[mode]}/{len(queries)}) | {total_latency:.2f} | {total_latency / len(queries):.2f} |"
        )

    lines.extend(
        [
            "",
            "The hybrid retriever combines the vector and BM25 rankings with Reciprocal Rank Fusion.",
            "",
            "## Hybrid Query Details",
            "",
            "| Query | Expected | Top 3 | Hit |",
            "|---|---|---|---|",
        ]
    )
    for query, expected, titles, hit in mode_rows["hybrid"]:
        lines.append(
            f"| {query} | {expected} | {'; '.join(titles)} | {'yes' if hit else 'no'} |"
        )

    lines.extend(
        [
            "",
            "## Vector vs BM25 Details",
            "",
        ]
    )
    for mode in ("vector", "bm25"):
        lines.extend(
            [
                f"### {mode}",
                "",
                "| Query | Expected | Top 3 | Hit |",
                "|---|---|---|---|",
            ]
        )
        for query, expected, titles, hit in mode_rows[mode]:
            lines.append(
                f"| {query} | {expected} | {'; '.join(titles)} | {'yes' if hit else 'no'} |"
            )

    report_path.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
