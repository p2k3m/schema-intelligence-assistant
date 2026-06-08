from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AGENT_DIR = ROOT / "agent"
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

from agent import SchemaIntelligenceAgent


QUERIES = [
    "What does DATE_SHIFT do?",
    "What parameters does EMAIL_MASK accept?",
    "How do I comply with GDPR when masking customer data?",
    "What is the capital of France?",
    "Mask this column: email_address",
]


def run_baseline() -> list[dict[str, object]]:
    agent = SchemaIntelligenceAgent()
    rows = []
    for query in QUERIES:
        response = agent.chat(query)
        rows.append(
            {
                "query": query,
                "baseline_a_score": _score_response(query, response),
                "baseline_b_score": 0,
                "notes": _notes(query, response),
            }
        )
    _write_report(rows)
    return rows


def _score_response(query: str, response: str) -> int:
    lowered_query = query.lower()
    lowered_response = response.lower()
    score = 0
    if "[source:" in lowered_response or "out of scope" in lowered_response or "provide" in lowered_response:
        score += 1
    if "date_shift" in lowered_query and "date" in lowered_response and "shift" in lowered_response:
        score += 1
    if "email_mask" in lowered_query and "email" in lowered_response:
        score += 1
    if "gdpr" in lowered_query and "gdpr" in lowered_response:
        score += 1
    if "capital of france" in lowered_query and "paris" not in lowered_response:
        score += 1
    if "mask this column" in lowered_query and "provide" in lowered_response:
        score += 1
    return min(score, 3)


def _notes(query: str, response: str) -> str:
    if "[Source:" in response:
        return "grounded with citation"
    if "Out of scope" in response:
        return "rejected out-of-scope query"
    if "provide" in response.lower():
        return "asked for missing schema"
    return f"needs review for query: {query}"


def _write_report(rows: list[dict[str, object]]) -> None:
    report_path = Path(__file__).with_name("ab_baseline_results.md")
    lines = [
        "# A/B Baseline Results",
        "",
        "Rubric: 0 to 3 points per response. One point each for correct routing, grounded or safe behavior, and task-specific completeness. Baseline B is a reserved future model slot.",
        "",
        "| Query | Baseline A | Baseline B | Notes |",
        "|---|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['query']} | {row['baseline_a_score']} | {row['baseline_b_score']} | {row['notes']} |"
        )
    report_path.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    run_baseline()
