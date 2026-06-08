from __future__ import annotations

import math
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

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


@dataclass(frozen=True)
class Candidate:
    name: str
    input_cost_per_million: float
    output_cost_per_million: float
    answer: Callable[[str], str]


def run_baseline() -> list[dict[str, object]]:
    candidates = [
        Candidate(
            name="Strict grounded policy (gpt-4o-mini fallback estimate)",
            input_cost_per_million=0.15,
            output_cost_per_million=0.60,
            answer=SchemaIntelligenceAgent().chat,
        ),
        Candidate(
            name=_loose_candidate_name(),
            input_cost_per_million=0.80,
            output_cost_per_million=4.00,
            answer=_loose_candidate_answer,
        ),
    ]

    rows = []
    for query in QUERIES:
        row: dict[str, object] = {"query": query}
        for index, candidate in enumerate(candidates, start=1):
            started = time.perf_counter()
            response = candidate.answer(query)
            latency_ms = (time.perf_counter() - started) * 1000
            input_tokens = _estimate_tokens(query)
            output_tokens = _estimate_tokens(response)
            row[f"candidate_{index}_name"] = candidate.name
            row[f"candidate_{index}_score"] = _score_response(query, response)
            row[f"candidate_{index}_latency_ms"] = round(latency_ms, 2)
            row[f"candidate_{index}_input_tokens"] = input_tokens
            row[f"candidate_{index}_output_tokens"] = output_tokens
            row[f"candidate_{index}_estimated_cost_usd"] = _estimate_cost(
                input_tokens,
                output_tokens,
                candidate.input_cost_per_million,
                candidate.output_cost_per_million,
            )
            row[f"candidate_{index}_notes"] = _notes(response)
        rows.append(row)

    _write_report(rows)
    return rows


def _loose_baseline_answer(query: str) -> str:
    lowered = query.lower()
    if "date_shift" in lowered:
        return "DATE_SHIFT changes dates by some offset."
    if "email_mask" in lowered:
        return "EMAIL_MASK hides parts of an email address."
    if "gdpr" in lowered:
        return "For GDPR, mask customer data and document your process."
    if "capital of france" in lowered:
        return "The capital of France is Paris."
    if "mask this column" in lowered:
        return "Use EMAIL_MASK for email_address."
    return "I can help."


def _loose_candidate_name() -> str:
    if os.getenv("SCHEMA_ASSISTANT_AB_USE_OLLAMA") == "true":
        model = os.getenv("SCHEMA_ASSISTANT_OLLAMA_MODEL", "llama3.2:1b")
        return f"Loose helpful policy (Ollama {model}, Claude 3.5 Haiku cost estimate)"
    return "Loose helpful policy (mocked, Claude 3.5 Haiku cost estimate)"


def _loose_candidate_answer(query: str) -> str:
    if os.getenv("SCHEMA_ASSISTANT_AB_USE_OLLAMA") != "true":
        return _loose_baseline_answer(query)

    model = os.getenv("SCHEMA_ASSISTANT_OLLAMA_MODEL", "llama3.2:1b")
    prompt = (
        "Answer helpfully but do not use retrieval tools. "
        "This is an intentionally loose baseline.\n\n"
        f"User: {query}"
    )
    try:
        completed = subprocess.run(
            ["ollama", "run", model, prompt],
            check=True,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.SubprocessError):
        return _loose_baseline_answer(query)
    return completed.stdout.strip() or _loose_baseline_answer(query)


def _score_response(query: str, response: str) -> int:
    lowered_query = query.lower()
    lowered_response = response.lower()
    score = 0

    if "[source:" in lowered_response or "out of scope" in lowered_response or "provide" in lowered_response:
        score += 1
    response_words = set(_words(lowered_response))
    if "date_shift" in lowered_query and (
        "date_shift" in lowered_response or {"date", "shift"} <= response_words
    ):
        score += 1
    if "email_mask" in lowered_query and "email" in lowered_response:
        score += 1
    if "gdpr" in lowered_query and "gdpr" in lowered_response and "[source:" in lowered_response:
        score += 1
    if "capital of france" in lowered_query and "paris" not in lowered_response and "out of scope" in lowered_response:
        score += 1
    if "mask this column" in lowered_query and "provide" in lowered_response and "schema" in lowered_response:
        score += 1
    return min(score, 3)


def _notes(response: str) -> str:
    lowered = response.lower()
    if "[source:" in lowered:
        return "grounded with citation"
    if "out of scope" in lowered:
        return "rejected before tool use"
    if "provide" in lowered:
        return "asks for missing schema"
    return "ungrounded or incomplete"


def _estimate_tokens(text: str) -> int:
    return max(1, math.ceil(len(text) / 4))


def _estimate_cost(
    input_tokens: int,
    output_tokens: int,
    input_cost_per_million: float,
    output_cost_per_million: float,
) -> float:
    return round(
        input_tokens * input_cost_per_million / 1_000_000
        + output_tokens * output_cost_per_million / 1_000_000,
        8,
    )


def _words(text: str) -> list[str]:
    return [word.strip(".,:;!?()[]`").lower() for word in text.split()]


def _write_report(rows: list[dict[str, object]]) -> None:
    report_path = Path(__file__).with_name("ab_baseline_results.md")
    lines = [
        "# A/B Baseline Results",
        "",
        "Rubric: 0 to 3 points per response. One point each for correct routing, grounded or safe behavior, and task-specific completeness.",
        "",
        "Pricing is estimated from configured per-million-token rates; the local test run does not call external APIs.",
        "Set `SCHEMA_ASSISTANT_AB_USE_OLLAMA=true` to replace the mocked loose candidate with a local Ollama model when available.",
        "",
        "| Query | Candidate A | A Score | A Latency ms | A Tokens in/out | A Estimated cost USD | Candidate B | B Score | B Latency ms | B Tokens in/out | B Estimated cost USD | Notes |",
        "|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            "| {query} | {a_name} | {a_score} | {a_latency} | {a_in}/{a_out} | {a_cost:.8f} | {b_name} | {b_score} | {b_latency} | {b_in}/{b_out} | {b_cost:.8f} | {notes} |".format(
                query=row["query"],
                a_name=row["candidate_1_name"],
                a_score=row["candidate_1_score"],
                a_latency=row["candidate_1_latency_ms"],
                a_in=row["candidate_1_input_tokens"],
                a_out=row["candidate_1_output_tokens"],
                a_cost=row["candidate_1_estimated_cost_usd"],
                b_name=row["candidate_2_name"],
                b_score=row["candidate_2_score"],
                b_latency=row["candidate_2_latency_ms"],
                b_in=row["candidate_2_input_tokens"],
                b_out=row["candidate_2_output_tokens"],
                b_cost=row["candidate_2_estimated_cost_usd"],
                notes=f"{row['candidate_1_notes']}; {row['candidate_2_notes']}",
            )
        )
    report_path.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    run_baseline()
