"""Document ingestion helpers for the masking documentation corpus."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DocumentChunk:
    title: str
    source: str
    content: str
    pii_category: str


FILE_CATEGORY_MAP: dict[str, tuple[str, ...]] = {
    "data_masking_overview.md": ("GENERAL",),
    "masking_functions_overview.md": ("GENERAL",),
    "name_randomize.md": ("FULL_NAME",),
    "email_mask.md": ("EMAIL",),
    "phone_ssn_mask.md": ("PHONE", "SSN"),
    "credit_card_account_mask.md": ("CREDIT_CARD", "ACCOUNT_NUMBER"),
    "date_shift.md": ("DATE_OF_BIRTH",),
    "address_ip_national_id_mask.md": ("ADDRESS", "IP_ADDRESS", "NATIONAL_ID"),
    "masking_job_configuration.md": ("GENERAL",),
    "gdpr_ccpa_compliance.md": ("GENERAL",),
    "troubleshooting.md": ("GENERAL",),
    "performance_tuning.md": ("GENERAL",),
}


def load_corpus(corpus_dir: str | Path | None = None) -> list[DocumentChunk]:
    root = Path(corpus_dir) if corpus_dir else Path(__file__).parent / "corpus"
    chunks: list[DocumentChunk] = []

    for path in sorted(root.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        title = _extract_title(text, path.stem.replace("_", " ").title())
        categories = FILE_CATEGORY_MAP.get(path.name, ("GENERAL",))
        for category in categories:
            chunks.append(
                DocumentChunk(
                    title=title,
                    source=path.name,
                    content=text,
                    pii_category=category,
                )
            )
    return chunks


def _extract_title(text: str, fallback: str) -> str:
    match = re.search(r"^#\s+(.+)$", text, flags=re.MULTILINE)
    return match.group(1).strip() if match else fallback
