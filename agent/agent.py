"""Local Schema Intelligence Agent.

The agent is a deterministic router around the three required tools. In a
production AWS setup, this router can sit behind Bedrock Converse or Agents,
but the grounding rule remains the same: documentation answers must first call
`search_masking_docs`.
"""

from __future__ import annotations

import json
import re
from typing import Any

try:
    from tools import detect_pii_columns, generate_masking_config, search_masking_docs
except ModuleNotFoundError:
    from .tools import detect_pii_columns, generate_masking_config, search_masking_docs


class SchemaIntelligenceAgent:
    def chat(
        self,
        user_message: str,
        schema: list[dict[str, Any]] | None = None,
        detections: list[dict[str, Any]] | None = None,
    ) -> str:
        message = user_message.strip()
        lowered = message.lower()

        if _is_out_of_scope(lowered):
            return (
                "Out of scope: I can help with schema PII detection, data masking "
                "configuration, and masking documentation questions."
            )

        if "mask this column" in lowered and not schema:
            return "Please provide the table name, column name, data type, and sample values before I recommend masking."

        if _asks_for_schema_analysis(lowered):
            if not schema:
                return "Please provide schema JSON so I can analyse columns for PII."
            return json.dumps({"detections": detect_pii_columns(schema)}, indent=2)

        if _asks_for_config(lowered):
            if detections is None:
                if not schema:
                    return "Please provide detection results or schema JSON before generating a masking configuration."
                detections = detect_pii_columns(schema)
            return json.dumps(generate_masking_config(detections), indent=2)

        single_column = _extract_single_column_question(message)
        if single_column:
            result = detect_pii_columns([single_column])[0]
            category = result["pii_category"] or "not PII"
            return (
                f"{single_column['table_name']}.{single_column['column_name']} is {category} "
                f"with confidence {result['confidence']:.2f}. Reasoning: {result['reasoning']}"
            )

        if _is_documentation_question(lowered):
            category_filter = _infer_category_filter(lowered)
            docs = search_masking_docs(message, category_filter)
            if not docs:
                return "I could not find grounded masking documentation for that question."
            return _grounded_answer(message, docs)

        return (
            "I can analyse schema JSON for PII, generate masking configuration JSON, "
            "or answer data masking documentation questions."
        )


def build_agent() -> SchemaIntelligenceAgent:
    return SchemaIntelligenceAgent()


agent = SchemaIntelligenceAgent()


def _asks_for_schema_analysis(message: str) -> bool:
    return ("analyse" in message or "analyze" in message) and "schema" in message


def _asks_for_config(message: str) -> bool:
    return "generate" in message and "masking configuration" in message


def _is_documentation_question(message: str) -> bool:
    doc_terms = (
        "what does",
        "what parameters",
        "how do i",
        "how should",
        "gdpr",
        "ccpa",
        "masking",
        "date_shift",
        "email_mask",
        "account_mask",
    )
    return any(term in message for term in doc_terms)


def _is_out_of_scope(message: str) -> bool:
    out_of_scope_terms = (
        "weather",
        "capital of france",
        "stock price",
        "sports",
        "recipe",
    )
    return any(term in message for term in out_of_scope_terms)


def _extract_single_column_question(message: str) -> dict[str, Any] | None:
    match = re.search(
        r"column\s+(?P<column>[A-Za-z0-9_]+)\s+in\s+table\s+(?P<table>[A-Za-z0-9_]+)",
        message,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    return {
        "table_name": match.group("table").upper(),
        "column_name": match.group("column"),
        "data_type": "UNKNOWN",
        "sample_values": [],
        "nullable": True,
    }


def _infer_category_filter(message: str) -> str | None:
    mapping = {
        "date_shift": "DATE_OF_BIRTH",
        "date shift": "DATE_OF_BIRTH",
        "email_mask": "EMAIL",
        "email": "EMAIL",
        "phone": "PHONE",
        "ssn": "SSN",
        "credit_card": "CREDIT_CARD",
        "credit card": "CREDIT_CARD",
        "account": "ACCOUNT_NUMBER",
        "address": "ADDRESS",
        "ip": "IP_ADDRESS",
        "national": "NATIONAL_ID",
    }
    for token, category in mapping.items():
        if token in message:
            return category
    return None


def _grounded_answer(_message: str, docs: list[dict[str, object]]) -> str:
    primary = docs[0]
    content = str(primary["content"])
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", content) if part.strip()]
    selected = " ".join(sentences[1:4] if len(sentences) > 3 else sentences[:3])
    return f"{selected} [Source: {primary['source']}]"


if __name__ == "__main__":
    print(agent.chat("What does DATE_SHIFT do and what parameters does it accept?"))
