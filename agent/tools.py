"""Tool layer used by the local Schema Intelligence Agent."""

from __future__ import annotations

import contextlib
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator


ROOT = Path(__file__).resolve().parents[1]
for relative in ("pii-detector", "masking-generator", "rag"):
    path = str(ROOT / relative)
    if path not in sys.path:
        sys.path.insert(0, path)

from detector import PiiDetector
from generator import MaskingConfigGenerator
from retrieve import retrieve


@dataclass
class ToolCallTracker:
    called_tools: list[str] = field(default_factory=list)


_ACTIVE_TRACKERS: list[ToolCallTracker] = []


@contextlib.contextmanager
def tool_call_tracker() -> Iterator[ToolCallTracker]:
    tracker = ToolCallTracker()
    _ACTIVE_TRACKERS.append(tracker)
    try:
        yield tracker
    finally:
        _ACTIVE_TRACKERS.remove(tracker)


def detect_pii_columns(schema: list[dict[str, Any]]) -> list[dict[str, Any]]:
    _record_tool("detect_pii_columns")
    return PiiDetector().detect_all(schema)


def generate_masking_config(detections: list[dict[str, Any]]) -> dict[str, Any]:
    _record_tool("generate_masking_config")
    return MaskingConfigGenerator().generate(detections)


def search_masking_docs(
    query: str, pii_category_filter: str | None = None
) -> list[dict[str, object]]:
    _record_tool("search_masking_docs")
    return retrieve(query=query, pii_category_filter=pii_category_filter, top_k=3)


def _record_tool(name: str) -> None:
    for tracker in _ACTIVE_TRACKERS:
        tracker.called_tools.append(name)

