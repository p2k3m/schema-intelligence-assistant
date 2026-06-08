"""PII detection engine for schema column descriptors.

The Day 1 implementation intentionally avoids an LLM call per column. A
deterministic hybrid scorer lets us test quality criteria repeatably while
capturing two strong real-world signals: semantic column names and sample
value patterns. Low-confidence cases are surfaced for human or future
LLM-assisted review.
"""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Callable

from pii_patterns import (
    AUTO_TAG_THRESHOLD,
    LLM_ESCALATION_HIGH,
    LLM_ESCALATION_LOW,
    MASKING_FUNCTIONS,
    PII_DETECTION_THRESHOLD,
    REVIEW_LOWER_BOUND,
)


@dataclass(frozen=True)
class CategoryRule:
    aliases: tuple[tuple[str, float], ...]
    sample_matcher: Callable[[list[str]], tuple[float, str | None]]
    type_boost: Callable[[str], float] = lambda _data_type: 0.0


class PiiDetector:
    """Classifies schema columns against the required PII categories."""

    def detect_all(self, schema: list[dict[str, Any]]) -> list[dict[str, Any]]:
        detections: list[dict[str, Any]] = []
        for column in schema:
            result = self.detect(column)
            detections.append(
                {
                    **result,
                    "table_name": column.get("table_name", ""),
                    "column_name": column.get("column_name", ""),
                    "data_type": column.get("data_type", ""),
                    "nullable": column.get("nullable", True),
                }
            )
        return detections

    def detect(self, column: dict[str, Any]) -> dict[str, Any]:
        table_name = str(column.get("table_name", ""))
        column_name = str(column.get("column_name", ""))
        data_type = str(column.get("data_type", ""))
        sample_values = [str(value) for value in column.get("sample_values", [])]

        text = _normalize_identifier(f"{table_name} {column_name}")
        reasons_by_category: dict[str, list[str]] = {}
        scores: dict[str, float] = {}

        for category, rule in CATEGORY_RULES.items():
            score = 0.0
            reasons: list[str] = []

            alias_score, alias_reason = _score_aliases(text, rule.aliases)
            if alias_score:
                score += alias_score
                reasons.append(alias_reason)

            sample_score, sample_reason = rule.sample_matcher(sample_values)
            if sample_score:
                score += sample_score
                if sample_reason:
                    reasons.append(sample_reason)

            type_score = rule.type_boost(data_type.upper())
            if type_score:
                score += type_score
                reasons.append("data type supports this PII category")

            table_score, table_reason = _table_context_score(category, table_name)
            if table_score and alias_score:
                score += table_score
                reasons.append(table_reason)

            scores[category] = min(score, 0.99)
            reasons_by_category[category] = reasons

        best_category = max(scores, key=scores.get)
        confidence = scores[best_category]
        direct_sample_signal = _has_direct_sample_signal(sample_values)

        if _is_known_non_pii(column_name) and not direct_sample_signal:
            confidence = min(confidence, 0.22)
            reasons_by_category[best_category] = ["column matches known non-PII operational identifier"]

        ambiguous_identifier = _has_ambiguous_identifier_signal(column_name)
        if confidence < REVIEW_LOWER_BOUND and ambiguous_identifier:
            confidence = 0.45
            reasons_by_category[best_category] = [
                "generic identifier pattern is ambiguous and needs review"
            ]

        is_pii = confidence >= PII_DETECTION_THRESHOLD
        llm_escalation_recommended = LLM_ESCALATION_LOW <= confidence < LLM_ESCALATION_HIGH
        review_required = confidence < AUTO_TAG_THRESHOLD and (
            is_pii or confidence >= REVIEW_LOWER_BOUND
        )

        if is_pii:
            pii_category: str | None = best_category
            masking_function: str | None = MASKING_FUNCTIONS[best_category]
            reasoning = "; ".join(reasons_by_category[best_category])
        else:
            pii_category = None
            masking_function = None
            reasoning = (
                "; ".join(reasons_by_category[best_category])
                if reasons_by_category[best_category]
                else "No strong PII name or sample-value signals found"
            )

        return {
            "is_pii": is_pii,
            "confidence": round(confidence, 2),
            "pii_category": pii_category,
            "recommended_masking_function": masking_function,
            "review_required": review_required,
            "llm_escalation_recommended": llm_escalation_recommended,
            "reasoning": reasoning,
        }


def _score_aliases(text: str, aliases: tuple[tuple[str, float], ...]) -> tuple[float, str]:
    best_score = 0.0
    best_alias = ""
    for alias, weight in aliases:
        if _contains_phrase(text, alias) and weight > best_score:
            best_score = weight
            best_alias = alias
    reason = f"column or table name matches '{best_alias}' pattern" if best_alias else ""
    return best_score, reason


def _normalize_identifier(value: str) -> str:
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", value)
    return re.sub(r"[^a-z0-9]+", " ", spaced.lower()).strip()


def _contains_phrase(text: str, phrase: str) -> bool:
    normalized_phrase = _normalize_identifier(phrase)
    return f" {normalized_phrase} " in f" {text} "


def _table_context_score(category: str, table_name: str) -> tuple[float, str]:
    table_text = _normalize_identifier(table_name)
    people_tables = ("customer", "customers", "user", "users", "employee", "employees", "patient", "patients")
    finance_tables = ("account", "accounts", "payment", "payments", "billing")

    if category in {"FULL_NAME", "EMAIL", "PHONE", "DATE_OF_BIRTH", "ADDRESS", "NATIONAL_ID"}:
        if any(_contains_phrase(table_text, token) for token in people_tables):
            return 0.04, "table context is person-centric"
    if category in {"CREDIT_CARD", "ACCOUNT_NUMBER"}:
        if any(_contains_phrase(table_text, token) for token in finance_tables):
            return 0.04, "table context is financial"
    return 0.0, ""


def _has_ambiguous_identifier_signal(column_name: str) -> bool:
    text = _normalize_identifier(column_name)
    ambiguous_tokens = ("ref", "reference", "code", "identifier", "number", "num", "no")
    return any(_contains_phrase(text, token) for token in ambiguous_tokens)


def _is_known_non_pii(column_name: str) -> bool:
    text = _normalize_identifier(column_name)
    exact_phrases = (
        "transaction id",
        "order id",
        "product id",
        "session id",
        "invoice number",
        "sku",
        "status",
        "account status",
        "card type",
        "created at",
        "updated at",
        "error message",
        "email template name",
        "email bounce count",
        "ip country",
        "ssn error count",
        "city",
        "order total",
        "product name",
    )
    return any(_contains_phrase(text, phrase) for phrase in exact_phrases)


def _nonnull_samples(samples: list[str]) -> list[str]:
    nullish = {"", "null", "none", "n/a", "na"}
    return [sample.strip() for sample in samples if sample and sample.strip().lower() not in nullish]


def _ratio(samples: list[str], predicate: Callable[[str], bool]) -> float:
    values = _nonnull_samples(samples)
    if not values:
        return 0.0
    return sum(1 for value in values if predicate(value)) / len(values)


def _score_from_ratio(ratio: float, strong: float, weak: float = 0.20) -> float:
    if ratio >= 0.67:
        return strong
    if ratio > 0:
        return weak
    return 0.0


def _email_samples(samples: list[str]) -> tuple[float, str | None]:
    ratio = _ratio(samples, lambda value: bool(EMAIL_RE.fullmatch(value)))
    score = _score_from_ratio(ratio, 0.42)
    return score, "sample values match email format" if score else None


def _phone_samples(samples: list[str]) -> tuple[float, str | None]:
    ratio = _ratio(samples, _looks_like_phone)
    score = _score_from_ratio(ratio, 0.36)
    return score, "sample values match phone number format" if score else None


def _ssn_samples(samples: list[str]) -> tuple[float, str | None]:
    ratio = _ratio(samples, lambda value: bool(SSN_RE.fullmatch(value.replace(" ", ""))))
    score = _score_from_ratio(ratio, 0.46)
    return score, "sample values match SSN format" if score else None


def _credit_card_samples(samples: list[str]) -> tuple[float, str | None]:
    ratio = _ratio(samples, _looks_like_credit_card)
    score = _score_from_ratio(ratio, 0.46)
    return score, "sample values pass credit card format checks" if score else None


def _account_samples(samples: list[str]) -> tuple[float, str | None]:
    ratio = _ratio(samples, _looks_like_account_number)
    score = _score_from_ratio(ratio, 0.36)
    return score, "sample values match account number format" if score else None


def _dob_samples(samples: list[str]) -> tuple[float, str | None]:
    ratio = _ratio(samples, _looks_like_birth_date)
    score = _score_from_ratio(ratio, 0.32, 0.12)
    return score, "sample values look like dates of birth" if score else None


def _address_samples(samples: list[str]) -> tuple[float, str | None]:
    ratio = _ratio(samples, _looks_like_address)
    score = _score_from_ratio(ratio, 0.36)
    return score, "sample values match postal address patterns" if score else None


def _ip_samples(samples: list[str]) -> tuple[float, str | None]:
    ratio = _ratio(samples, _looks_like_ip_address)
    score = _score_from_ratio(ratio, 0.44)
    return score, "sample values match IP address format" if score else None


def _national_id_samples(samples: list[str]) -> tuple[float, str | None]:
    ratio = _ratio(samples, _looks_like_national_id)
    score = _score_from_ratio(ratio, 0.38)
    return score, "sample values match national identifier format" if score else None


def _full_name_samples(samples: list[str]) -> tuple[float, str | None]:
    ratio = _ratio(samples, _looks_like_person_name)
    score = _score_from_ratio(ratio, 0.28, 0.10)
    return score, "sample values look like person names" if score else None


def _looks_like_phone(value: str) -> bool:
    digits = re.sub(r"\D", "", value)
    if not 10 <= len(digits) <= 15:
        return False
    return bool(PHONE_HINT_RE.search(value)) or value.strip().startswith("+")


def _looks_like_credit_card(value: str) -> bool:
    digits = re.sub(r"\D", "", value)
    return 13 <= len(digits) <= 19 and _luhn_valid(digits)


def _looks_like_account_number(value: str) -> bool:
    cleaned = value.strip().upper()
    if cleaned.startswith("ACC-"):
        return True
    if re.fullmatch(r"\*{2,}\d{4}", cleaned):
        return True
    if re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{11,30}", cleaned):
        return True
    return False


def _looks_like_birth_date(value: str) -> bool:
    formats = ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d")
    for fmt in formats:
        try:
            parsed = datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
        age = (date.today() - parsed).days / 365.25
        return 0 <= age <= 120
    return False


def _looks_like_address(value: str) -> bool:
    return bool(ADDRESS_RE.search(value))


def _looks_like_ip_address(value: str) -> bool:
    try:
        ipaddress.ip_address(value.strip())
    except ValueError:
        return False
    return True


def _looks_like_national_id(value: str) -> bool:
    cleaned = value.strip().upper().replace(" ", "")
    return bool(NINO_RE.fullmatch(cleaned) or AADHAAR_RE.fullmatch(cleaned) or PASSPORT_RE.fullmatch(cleaned))


def _looks_like_person_name(value: str) -> bool:
    stripped = value.strip()
    if not re.fullmatch(r"[A-Za-z][A-Za-z.'-]+(?: [A-Za-z][A-Za-z.'-]+){1,3}", stripped):
        return False
    return not any(char.isdigit() for char in stripped)


def _luhn_valid(digits: str) -> bool:
    checksum = 0
    parity = len(digits) % 2
    for index, char in enumerate(digits):
        digit = int(char)
        if index % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0


def _has_direct_sample_signal(samples: list[str]) -> bool:
    return any(
        matcher(samples)[0] >= 0.36
        for matcher in (
            _email_samples,
            _phone_samples,
            _ssn_samples,
            _credit_card_samples,
            _account_samples,
            _address_samples,
            _ip_samples,
            _national_id_samples,
        )
    )


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_HINT_RE = re.compile(r"[\s().-]")
SSN_RE = re.compile(r"\d{3}-?\d{2}-?\d{4}")
ADDRESS_RE = re.compile(
    r"\b\d{1,6}\s+[A-Za-z0-9.' -]+\s+"
    r"(street|st|avenue|ave|road|rd|lane|ln|drive|dr|way|blvd|boulevard)\b",
    re.IGNORECASE,
)
NINO_RE = re.compile(r"[A-Z]{2}\d{6}[A-Z]")
AADHAAR_RE = re.compile(r"\d{12}")
PASSPORT_RE = re.compile(r"[A-Z][0-9]{7}")


CATEGORY_RULES: dict[str, CategoryRule] = {
    "FULL_NAME": CategoryRule(
        aliases=(
            ("full_name", 0.72),
            ("full name", 0.72),
            ("legal_name", 0.70),
            ("person_name", 0.68),
            ("customer_name", 0.66),
            ("contact_name", 0.64),
            ("first_name", 0.62),
            ("last_name", 0.62),
            ("given_name", 0.62),
            ("surname", 0.62),
        ),
        sample_matcher=_full_name_samples,
    ),
    "EMAIL": CategoryRule(
        aliases=(
            ("email_address", 0.74),
            ("email", 0.72),
            ("e_mail", 0.72),
            ("correo_electronico", 0.74),
            ("mail_addr", 0.70),
            ("contact_email", 0.72),
        ),
        sample_matcher=_email_samples,
    ),
    "PHONE": CategoryRule(
        aliases=(
            ("phone_number", 0.72),
            ("mobile_phone", 0.72),
            ("telephone", 0.68),
            ("cell_phone", 0.70),
            ("msisdn", 0.74),
            ("fax_number", 0.64),
            ("phone", 0.66),
        ),
        sample_matcher=_phone_samples,
    ),
    "SSN": CategoryRule(
        aliases=(
            ("ssn", 0.78),
            ("social_security_number", 0.82),
            ("social security number", 0.82),
        ),
        sample_matcher=_ssn_samples,
    ),
    "CREDIT_CARD": CategoryRule(
        aliases=(
            ("credit_card_number", 0.82),
            ("credit card number", 0.82),
            ("card_number", 0.74),
            ("cc_number", 0.76),
            ("cc_num", 0.76),
            ("payment_card", 0.70),
        ),
        sample_matcher=_credit_card_samples,
    ),
    "ACCOUNT_NUMBER": CategoryRule(
        aliases=(
            ("account_number", 0.76),
            ("account_no", 0.74),
            ("acct_no", 0.76),
            ("acct_num", 0.76),
            ("cust_acct_no", 0.78),
            ("bank_account", 0.76),
            ("iban", 0.76),
        ),
        sample_matcher=_account_samples,
    ),
    "DATE_OF_BIRTH": CategoryRule(
        aliases=(
            ("date_of_birth", 0.82),
            ("birth_date", 0.80),
            ("birthdate", 0.80),
            ("dob", 0.82),
        ),
        sample_matcher=_dob_samples,
        type_boost=lambda data_type: 0.05 if "DATE" in data_type else 0.0,
    ),
    "ADDRESS": CategoryRule(
        aliases=(
            ("street_address", 0.76),
            ("shipping_address", 0.76),
            ("billing_address", 0.76),
            ("home_address", 0.76),
            ("postal_address", 0.74),
            ("address_line", 0.74),
            ("home_street", 0.72),
            ("address", 0.68),
        ),
        sample_matcher=_address_samples,
    ),
    "IP_ADDRESS": CategoryRule(
        aliases=(
            ("ip_address", 0.78),
            ("last_login_ip", 0.76),
            ("login_ip", 0.74),
            ("client_ip", 0.74),
            ("ipv4", 0.72),
            ("ipv6", 0.72),
        ),
        sample_matcher=_ip_samples,
    ),
    "NATIONAL_ID": CategoryRule(
        aliases=(
            ("national_id", 0.80),
            ("national_identifier", 0.78),
            ("national_insurance_number", 0.84),
            ("nat_ins_no", 0.82),
            ("nino", 0.78),
            ("passport_number", 0.78),
            ("passport_no", 0.78),
            ("tax_id", 0.74),
            ("aadhaar_no", 0.82),
            ("driver_license", 0.76),
            ("government_id", 0.78),
        ),
        sample_matcher=_national_id_samples,
    ),
}
