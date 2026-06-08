"""LangGraph-based local Schema Intelligence Agent."""

from __future__ import annotations

import json
import re
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

try:
    from tools import detect_pii_columns, generate_masking_config, search_masking_docs
except ModuleNotFoundError:
    from .tools import detect_pii_columns, generate_masking_config, search_masking_docs


ROUTE_OUT_OF_SCOPE = "out_of_scope"
ROUTE_NEEDS_SCHEMA = "needs_schema"
ROUTE_ANALYSE_SCHEMA = "analyse_schema"
ROUTE_GENERATE_CONFIG = "generate_config"
ROUTE_SINGLE_COLUMN = "single_column"
ROUTE_DOCS = "docs"
ROUTE_HELP = "help"


class AgentState(TypedDict, total=False):
    user_message: str
    schema: list[dict[str, Any]]
    detections: list[dict[str, Any]]
    route: str
    single_column: dict[str, Any]
    category_filter: str | None
    docs: list[dict[str, object]]
    masking_config: dict[str, Any]
    response: str
    current_tool: str
    tool_call_order: list[str]


class SchemaIntelligenceAgent:
    """StateGraph tool orchestrator for schema intelligence tasks.

    The graph is intentionally deterministic for local evaluation: intent is
    classified by structured rules, then conditional edges force each route to
    the correct tool node. Documentation routes cannot synthesize a response
    until `search_masking_docs` has populated `docs`; out-of-scope routes end
    before any tool node can run. For config generation from raw schema, the
    graph cycles through detection first, then calls the generator.
    """

    def __init__(self) -> None:
        self.graph = build_graph()

    def chat(
        self,
        user_message: str,
        schema: list[dict[str, Any]] | None = None,
        detections: list[dict[str, Any]] | None = None,
    ) -> str:
        return self.run_with_state(user_message, schema=schema, detections=detections)["response"]

    def run_with_state(
        self,
        user_message: str,
        schema: list[dict[str, Any]] | None = None,
        detections: list[dict[str, Any]] | None = None,
    ) -> AgentState:
        state: AgentState = {
            "user_message": user_message.strip(),
            "tool_call_order": [],
        }
        if schema is not None:
            state["schema"] = schema
        if detections is not None:
            state["detections"] = detections
        return self.graph.invoke(state)


def build_agent() -> SchemaIntelligenceAgent:
    return SchemaIntelligenceAgent()


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("call_tool", call_tool)
    graph.add_node("synthesize_response", synthesize_response)
    graph.add_node("handle_out_of_scope", handle_out_of_scope)

    graph.set_entry_point("classify_intent")
    graph.add_conditional_edges(
        "classify_intent",
        route_after_classification,
        {
            "tool": "call_tool",
            "synthesize": "synthesize_response",
            "out_of_scope": "handle_out_of_scope",
        },
    )
    graph.add_conditional_edges(
        "call_tool",
        route_after_tool,
        {
            "continue": "call_tool",
            "synthesize": "synthesize_response",
        },
    )
    graph.add_edge("synthesize_response", END)
    graph.add_edge("handle_out_of_scope", END)
    return graph.compile()


def classify_intent(state: AgentState) -> AgentState:
    message = state["user_message"]
    lowered = message.lower()
    route = _route(message, schema=state.get("schema"), detections=state.get("detections"))
    update: AgentState = {"route": route}

    if route == ROUTE_SINGLE_COLUMN:
        single_column = _extract_single_column_question(message)
        if single_column:
            update["single_column"] = single_column
            update["current_tool"] = "detect_pii_columns"
    elif route == ROUTE_ANALYSE_SCHEMA:
        update["current_tool"] = "detect_pii_columns"
    elif route == ROUTE_GENERATE_CONFIG:
        update["current_tool"] = (
            "generate_masking_config" if state.get("detections") else "detect_pii_columns"
        )
    elif route == ROUTE_DOCS:
        update["current_tool"] = "search_masking_docs"
        update["category_filter"] = _infer_category_filter(lowered)
    return update


def call_tool(state: AgentState) -> AgentState:
    tool_name = state["current_tool"]
    call_order = [*state.get("tool_call_order", []), tool_name]

    if tool_name == "detect_pii_columns":
        schema = state.get("schema") or [state["single_column"]]
        detections = detect_pii_columns(schema)
        update: AgentState = {"detections": detections, "tool_call_order": call_order}
        if state["route"] == ROUTE_GENERATE_CONFIG:
            update["current_tool"] = "generate_masking_config"
        return update

    if tool_name == "generate_masking_config":
        return {
            "masking_config": generate_masking_config(state["detections"]),
            "tool_call_order": call_order,
        }

    if tool_name == "search_masking_docs":
        return {
            "docs": search_masking_docs(
                state["user_message"],
                state.get("category_filter"),
            ),
            "tool_call_order": call_order,
        }

    return {"tool_call_order": call_order}


def synthesize_response(state: AgentState) -> AgentState:
    route = state["route"]

    if route == ROUTE_NEEDS_SCHEMA:
        return {
            "response": "Please provide the table name, column name, data type, and sample values before I recommend masking."
        }

    if route == ROUTE_ANALYSE_SCHEMA:
        if "schema" not in state:
            return {"response": "Please provide schema JSON so I can analyse columns for PII."}
        return {"response": json.dumps({"detections": state["detections"]}, indent=2)}

    if route == ROUTE_GENERATE_CONFIG:
        if "masking_config" not in state:
            return {
                "response": "Please provide detection results or schema JSON before generating a masking configuration."
            }
        return {"response": json.dumps(state["masking_config"], indent=2)}

    if route == ROUTE_SINGLE_COLUMN:
        result = state["detections"][0]
        single_column = state["single_column"]
        if result["review_required"] and not result["is_pii"]:
            return {
                "response": (
                    f"{single_column['table_name']}.{single_column['column_name']} is ambiguous, "
                    "not auto-classified as PII, and requires human review. "
                    f"Confidence: {result['confidence']:.2f}. Reasoning: {result['reasoning']}"
                )
            }
        category = result["pii_category"] or "not PII"
        return {
            "response": (
                f"{single_column['table_name']}.{single_column['column_name']} is {category} "
                f"with confidence {result['confidence']:.2f}. Reasoning: {result['reasoning']}"
            )
        }

    if route == ROUTE_DOCS:
        docs = state.get("docs", [])
        if not docs:
            return {"response": "I could not find grounded masking documentation for that question."}
        return {"response": _grounded_answer(state["user_message"], docs)}

    return {
        "response": (
            "I can analyse schema JSON for PII, generate masking configuration JSON, "
            "or answer data masking documentation questions."
        )
    }


def handle_out_of_scope(_state: AgentState) -> AgentState:
    return {
        "response": (
            "Out of scope: I can help with schema PII detection, data masking "
            "configuration, and masking documentation questions."
        )
    }


def route_after_classification(state: AgentState) -> str:
    if state["route"] == ROUTE_OUT_OF_SCOPE:
        return "out_of_scope"
    if state["route"] in {ROUTE_NEEDS_SCHEMA, ROUTE_HELP}:
        return "synthesize"
    if state["route"] == ROUTE_ANALYSE_SCHEMA and "schema" not in state:
        return "synthesize"
    if state["route"] == ROUTE_GENERATE_CONFIG and not state.get("detections") and "schema" not in state:
        return "synthesize"
    return "tool"


def route_after_tool(state: AgentState) -> str:
    if state["route"] == ROUTE_GENERATE_CONFIG and "masking_config" not in state:
        return "continue"
    return "synthesize"


agent = SchemaIntelligenceAgent()


def _route(
    message: str,
    schema: list[dict[str, Any]] | None = None,
    detections: list[dict[str, Any]] | None = None,
) -> str:
    lowered = message.lower()
    if _is_out_of_scope(lowered):
        return ROUTE_OUT_OF_SCOPE
    if "mask this column" in lowered and not schema:
        return ROUTE_NEEDS_SCHEMA
    if _asks_for_schema_analysis(lowered):
        return ROUTE_ANALYSE_SCHEMA
    if _asks_for_config(lowered):
        return ROUTE_GENERATE_CONFIG
    if _extract_single_column_question(message):
        return ROUTE_SINGLE_COLUMN
    if _is_documentation_question(lowered):
        return ROUTE_DOCS
    return ROUTE_HELP


def _asks_for_schema_analysis(message: str) -> bool:
    analysis_terms = ("analyse", "analyze", "scan", "find", "identify", "detect", "inspect")
    schema_terms = ("schema", "columns", "fields", "database", "table list", "tables")
    pii_terms = ("pii", "sensitive", "personal")
    return (
        any(term in message for term in analysis_terms)
        and any(term in message for term in schema_terms)
        and any(term in message for term in pii_terms)
    )


def _asks_for_config(message: str) -> bool:
    action_terms = ("generate", "create", "build", "produce")
    config_terms = ("masking configuration", "masking rules", "masking policy", "masking config")
    return any(term in message for term in action_terms) and any(
        term in message for term in config_terms
    )


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
    patterns = (
        r"(?:column|field)\s+(?P<column>[A-Za-z0-9_]+)\s+in\s+table\s+(?P<table>[A-Za-z0-9_]+)",
        r"(?:column|field)\s+(?P<column>[A-Za-z0-9_]+)\s+in\s+(?P<table>[A-Za-z0-9_]+)",
        r"(?:is|classify)\s+(?P<table>[A-Za-z0-9_]+)\.(?P<column>[A-Za-z0-9_]+)",
    )
    match = None
    for pattern in patterns:
        match = re.search(pattern, message, flags=re.IGNORECASE)
        if match:
            break
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
    query_terms = _content_terms(_message)
    candidates: list[tuple[int, str, str]] = []
    for doc in docs:
        source = str(doc["source"])
        for section in _sections(str(doc["content"])):
            score = len(query_terms & _content_terms(section))
            if "parameters" in query_terms and "parameters" in section.lower():
                score += 2
            if "what does" in _message.lower() and "usage" in section.lower():
                score += 2
            candidates.append((score, section, source))

    candidates.sort(key=lambda item: item[0], reverse=True)
    selected = [candidate for candidate in candidates if candidate[0] > 0][:2]
    if not selected:
        selected = candidates[:1]

    parts = []
    for _score, section, source in selected:
        sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", section) if part.strip()]
        snippet = " ".join(sentences[:2]).strip()
        parts.append(f"{snippet} [Source: {source}]")
    return " ".join(parts)


def _sections(markdown: str) -> list[str]:
    raw_sections = re.split(r"^##\s+", markdown, flags=re.MULTILINE)
    return [
        re.sub(r"\s+", " ", re.sub(r"^#+\s*", "", section, flags=re.MULTILINE)).strip()
        for section in raw_sections
        if section.strip()
    ]


def _content_terms(text: str) -> set[str]:
    stopwords = {
        "a",
        "an",
        "and",
        "are",
        "does",
        "do",
        "for",
        "how",
        "i",
        "is",
        "it",
        "of",
        "the",
        "to",
        "what",
        "when",
        "with",
    }
    return {
        token
        for token in re.findall(r"[a-z0-9_]+", text.lower())
        if token not in stopwords
    }


if __name__ == "__main__":
    print(agent.chat("What does DATE_SHIFT do and what parameters does it accept?"))
