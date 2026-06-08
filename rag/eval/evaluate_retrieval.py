import json
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from retrieve import retrieve


def main() -> None:
    query_path = Path(__file__).with_name("masking_queries.json")
    report_path = Path(__file__).with_name("recall_report.md")
    queries = json.loads(query_path.read_text())
    rows = []
    hits = 0

    for item in queries:
        results = retrieve(item["query"], top_k=3)
        titles = [result["title"] for result in results]
        hit = item["expected_source_title"] in titles
        hits += int(hit)
        rows.append((item["query"], item["expected_source_title"], titles, hit))

    recall = hits / len(queries)
    lines = [
        "# RAG Recall Report",
        "",
        f"Recall@3: {recall:.2f} ({hits}/{len(queries)})",
        "",
        "| Query | Expected | Top 3 | Hit |",
        "|---|---|---|---|",
    ]
    for query, expected, titles, hit in rows:
        lines.append(
            f"| {query} | {expected} | {'; '.join(titles)} | {'yes' if hit else 'no'} |"
        )

    report_path.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()

