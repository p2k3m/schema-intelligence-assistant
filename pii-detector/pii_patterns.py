"""Shared PII categories, thresholds, and documentation mappings."""

PII_CATEGORIES = (
    "FULL_NAME",
    "EMAIL",
    "PHONE",
    "SSN",
    "CREDIT_CARD",
    "ACCOUNT_NUMBER",
    "DATE_OF_BIRTH",
    "ADDRESS",
    "IP_ADDRESS",
    "NATIONAL_ID",
)

MASKING_FUNCTIONS: dict[str, str] = {
    "FULL_NAME": "NAME_RANDOMIZE",
    "EMAIL": "EMAIL_MASK",
    "PHONE": "PHONE_MASK",
    "SSN": "SSN_MASK",
    "CREDIT_CARD": "CREDIT_CARD_MASK",
    "ACCOUNT_NUMBER": "ACCOUNT_MASK",
    "DATE_OF_BIRTH": "DATE_SHIFT",
    "ADDRESS": "ADDRESS_RANDOMIZE",
    "IP_ADDRESS": "IP_MASK",
    "NATIONAL_ID": "NATIONAL_ID_MASK",
}

DOCUMENTATION_REFERENCES: dict[str, str] = {
    "FULL_NAME": "name_randomize.md#usage",
    "EMAIL": "email_mask.md#usage",
    "PHONE": "phone_ssn_mask.md#phone_mask",
    "SSN": "phone_ssn_mask.md#ssn_mask",
    "CREDIT_CARD": "credit_card_account_mask.md#credit_card_mask",
    "ACCOUNT_NUMBER": "credit_card_account_mask.md#account_mask",
    "DATE_OF_BIRTH": "date_shift.md#usage",
    "ADDRESS": "address_ip_national_id_mask.md#address_randomize",
    "IP_ADDRESS": "address_ip_national_id_mask.md#ip_mask",
    "NATIONAL_ID": "address_ip_national_id_mask.md#national_id_mask",
}

AUTO_TAG_THRESHOLD = 0.80
PII_DETECTION_THRESHOLD = 0.60
REVIEW_LOWER_BOUND = 0.35

