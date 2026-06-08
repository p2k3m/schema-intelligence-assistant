# Masking Functions Overview

Masking functions should match the risk and structure of the source column. `NAME_RANDOMIZE` generates plausible names. `EMAIL_MASK` preserves domain policy while hiding the mailbox. `PHONE_MASK` hides subscriber digits. `SSN_MASK`, `NATIONAL_ID_MASK`, `CREDIT_CARD_MASK`, and `ACCOUNT_MASK` protect regulated identifiers.

`DATE_SHIFT` changes dates by a configured offset while preserving valid date values and, when requested, relative spacing. `ADDRESS_RANDOMIZE` swaps postal fields with realistic alternatives. `IP_MASK` redacts or subnet-preserves IP addresses for logs and audit records.

When deciding which masking function to use for names, emails, phone numbers, SSNs, credit cards, account numbers, dates of birth, addresses, IP addresses, and national IDs, start with this overview and then open the function-specific guide for parameters.

Prefer deterministic masking when joins, repeatable tests, or referential integrity matter. Prefer randomized masking when every run should produce fresh values and no downstream key relationship depends on the original value.
