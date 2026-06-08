"""Masking configuration generator."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from pii_patterns import DOCUMENTATION_REFERENCES, MASKING_FUNCTIONS


@dataclass(frozen=True)
class DetectionResult:
    column: str
    table: str
    is_pii: bool
    confidence: float
    pii_category: str | None
    recommended_masking_function: str | None = None
    review_required: bool = False
    reasoning: str = ""


class MaskingConfigGenerator:
    def generate(self, detections: list[DetectionResult | dict[str, Any]]) -> dict[str, Any]:
        normalized = [_normalize_detection(detection) for detection in detections]
        rules = []
        review_queue = []

        for detection in normalized:
            if not detection["is_pii"]:
                continue

            if detection["review_required"] or detection["confidence"] < 0.80:
                review_queue.append(_review_item(detection))
                continue

            category = detection["pii_category"]
            rules.append(
                {
                    "table": detection["table"],
                    "column": detection["column"],
                    "masking_function": detection["recommended_masking_function"],
                    "parameters": {},
                    "confidence": detection["confidence"],
                    "requires_review": False,
                    "documentation_reference": DOCUMENTATION_REFERENCES[category],
                }
            )

        return {
            "masking_job_name": f"AUTO_GENERATED_{date.today().isoformat()}",
            "generated_by": "SchemaIntelligenceAssistant",
            "confidence_summary": {
                "auto_configured": len(rules),
                "requires_review": len(review_queue),
                "not_pii": sum(1 for detection in normalized if not detection["is_pii"]),
            },
            "masking_rules": rules,
            "review_queue": review_queue,
        }


def generate(detections: list[DetectionResult | dict[str, Any]]) -> dict[str, Any]:
    return MaskingConfigGenerator().generate(detections)


def _normalize_detection(detection: DetectionResult | dict[str, Any]) -> dict[str, Any]:
    if isinstance(detection, DetectionResult):
        category = detection.pii_category
        return {
            "table": detection.table,
            "column": detection.column,
            "is_pii": detection.is_pii,
            "confidence": detection.confidence,
            "pii_category": category,
            "recommended_masking_function": detection.recommended_masking_function
            or (MASKING_FUNCTIONS[category] if category else None),
            "review_required": detection.review_required,
            "reasoning": detection.reasoning,
        }

    category = detection.get("pii_category")
    return {
        "table": detection.get("table")
        or detection.get("table_name")
        or detection.get("tableName")
        or "",
        "column": detection.get("column")
        or detection.get("column_name")
        or detection.get("columnName")
        or "",
        "is_pii": bool(detection.get("is_pii")),
        "confidence": float(detection.get("confidence", 0.0)),
        "pii_category": category,
        "recommended_masking_function": detection.get("recommended_masking_function")
        or (MASKING_FUNCTIONS[category] if category else None),
        "review_required": bool(detection.get("review_required")),
        "reasoning": detection.get("reasoning", ""),
    }


def _review_item(detection: dict[str, Any]) -> dict[str, Any]:
    suggested = detection["recommended_masking_function"]
    alternatives = [
        function
        for function in MASKING_FUNCTIONS.values()
        if function != suggested
    ][:3]
    reason = detection["reasoning"] or "Column requires human validation before masking"
    return {
        "table": detection["table"],
        "column": detection["column"],
        "reason": f"Low confidence ({detection['confidence']:.2f}) - {reason}",
        "suggested_function": suggested,
        "alternatives": alternatives,
    }

