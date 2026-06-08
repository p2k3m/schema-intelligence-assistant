"""FastAPI wrapper for the local Schema Intelligence Assistant."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field

try:
    from agent.agent import SchemaIntelligenceAgent
except ModuleNotFoundError:
    from agent import SchemaIntelligenceAgent


app = FastAPI(title="Schema Intelligence Assistant")
agent = SchemaIntelligenceAgent()


class ChatRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    message: str
    schema_: list[dict[str, Any]] | None = Field(default=None, alias="schema")
    detections: list[dict[str, Any]] | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat")
def chat(request: ChatRequest) -> dict[str, str]:
    return {
        "response": agent.chat(
            request.message,
            schema=request.schema_,
            detections=request.detections,
        )
    }


@app.post("/analyze")
def analyze(schema: list[dict[str, Any]]) -> dict[str, str]:
    return {"response": agent.chat("Analyse this schema for PII", schema=schema)}
