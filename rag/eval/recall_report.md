# RAG Recall Report

Hybrid Recall@3: 1.00 (13/13)

| Retriever | Recall@3 | Total latency ms | Avg latency ms/query |
|---|---:|---:|---:|
| vector | 1.00 (13/13) | 29.18 | 2.24 |
| bm25 | 0.92 (12/13) | 28.63 | 2.20 |
| hybrid | 1.00 (13/13) | 28.54 | 2.20 |

The hybrid retriever combines the vector and BM25 rankings with Reciprocal Rank Fusion.

## Hybrid Query Details

| Query | Expected | Top 3 | Hit |
|---|---|---|---|
| what is data masking and why do enterprises use it | What Is Data Masking | What Is Data Masking; Configuring and Running a Masking Job; GDPR and CCPA Compliance | yes |
| which masking function should I use for names emails and accounts | Masking Functions Overview | Masking Functions Overview; GDPR and CCPA Compliance; Configuring and Running a Masking Job | yes |
| how does NAME_RANDOMIZE work for customer full names | NAME_RANDOMIZE | NAME_RANDOMIZE; Masking Functions Overview; ADDRESS_RANDOMIZE, IP_MASK, and NATIONAL_ID_MASK | yes |
| what parameters does EMAIL_MASK accept | EMAIL_MASK | EMAIL_MASK; What Is Data Masking; Masking Functions Overview | yes |
| how should phone numbers and SSNs be masked | PHONE_MASK and SSN_MASK | GDPR and CCPA Compliance; PHONE_MASK and SSN_MASK; Masking Functions Overview | yes |
| how do CREDIT_CARD_MASK and ACCOUNT_MASK protect financial identifiers | CREDIT_CARD_MASK and ACCOUNT_MASK | CREDIT_CARD_MASK and ACCOUNT_MASK; CREDIT_CARD_MASK and ACCOUNT_MASK; Masking Functions Overview | yes |
| what does DATE_SHIFT do and does it preserve date format | DATE_SHIFT | DATE_SHIFT; Common Masking Errors and Troubleshooting; Masking Functions Overview | yes |
| how do I mask postal addresses IP addresses and national IDs | ADDRESS_RANDOMIZE, IP_MASK, and NATIONAL_ID_MASK | Masking Functions Overview; GDPR and CCPA Compliance; ADDRESS_RANDOMIZE, IP_MASK, and NATIONAL_ID_MASK | yes |
| how do I configure and run a masking job | Configuring and Running a Masking Job | Configuring and Running a Masking Job; Common Masking Errors and Troubleshooting; Masking Functions Overview | yes |
| how do GDPR and CCPA affect data masking workflows | GDPR and CCPA Compliance | GDPR and CCPA Compliance; What Is Data Masking; Configuring and Running a Masking Job | yes |
| how can I keep customer age distribution realistic without exposing birth date | DATE_SHIFT | DATE_SHIFT; NAME_RANDOMIZE; What Is Data Masking | yes |
| mask payment identifier but keep last four digits for support lookup | CREDIT_CARD_MASK and ACCOUNT_MASK | PHONE_MASK and SSN_MASK; CREDIT_CARD_MASK and ACCOUNT_MASK; PHONE_MASK and SSN_MASK | yes |
| developers need realistic test data but should not see real names | NAME_RANDOMIZE | NAME_RANDOMIZE; What Is Data Masking; GDPR and CCPA Compliance | yes |

## Vector vs BM25 Details

### vector

| Query | Expected | Top 3 | Hit |
|---|---|---|---|
| what is data masking and why do enterprises use it | What Is Data Masking | What Is Data Masking; Configuring and Running a Masking Job; GDPR and CCPA Compliance | yes |
| which masking function should I use for names emails and accounts | Masking Functions Overview | Masking Functions Overview; GDPR and CCPA Compliance; Configuring and Running a Masking Job | yes |
| how does NAME_RANDOMIZE work for customer full names | NAME_RANDOMIZE | NAME_RANDOMIZE; Masking Functions Overview; ADDRESS_RANDOMIZE, IP_MASK, and NATIONAL_ID_MASK | yes |
| what parameters does EMAIL_MASK accept | EMAIL_MASK | EMAIL_MASK; What Is Data Masking; Masking Functions Overview | yes |
| how should phone numbers and SSNs be masked | PHONE_MASK and SSN_MASK | GDPR and CCPA Compliance; PHONE_MASK and SSN_MASK; PHONE_MASK and SSN_MASK | yes |
| how do CREDIT_CARD_MASK and ACCOUNT_MASK protect financial identifiers | CREDIT_CARD_MASK and ACCOUNT_MASK | CREDIT_CARD_MASK and ACCOUNT_MASK; CREDIT_CARD_MASK and ACCOUNT_MASK; Masking Functions Overview | yes |
| what does DATE_SHIFT do and does it preserve date format | DATE_SHIFT | DATE_SHIFT; Common Masking Errors and Troubleshooting; Masking Functions Overview | yes |
| how do I mask postal addresses IP addresses and national IDs | ADDRESS_RANDOMIZE, IP_MASK, and NATIONAL_ID_MASK | Masking Functions Overview; GDPR and CCPA Compliance; ADDRESS_RANDOMIZE, IP_MASK, and NATIONAL_ID_MASK | yes |
| how do I configure and run a masking job | Configuring and Running a Masking Job | Configuring and Running a Masking Job; Common Masking Errors and Troubleshooting; Masking Functions Overview | yes |
| how do GDPR and CCPA affect data masking workflows | GDPR and CCPA Compliance | GDPR and CCPA Compliance; What Is Data Masking; Configuring and Running a Masking Job | yes |
| how can I keep customer age distribution realistic without exposing birth date | DATE_SHIFT | DATE_SHIFT; NAME_RANDOMIZE; What Is Data Masking | yes |
| mask payment identifier but keep last four digits for support lookup | CREDIT_CARD_MASK and ACCOUNT_MASK | PHONE_MASK and SSN_MASK; PHONE_MASK and SSN_MASK; CREDIT_CARD_MASK and ACCOUNT_MASK | yes |
| developers need realistic test data but should not see real names | NAME_RANDOMIZE | NAME_RANDOMIZE; What Is Data Masking; GDPR and CCPA Compliance | yes |
### bm25

| Query | Expected | Top 3 | Hit |
|---|---|---|---|
| what is data masking and why do enterprises use it | What Is Data Masking | What Is Data Masking; Configuring and Running a Masking Job; GDPR and CCPA Compliance | yes |
| which masking function should I use for names emails and accounts | Masking Functions Overview | Masking Functions Overview; GDPR and CCPA Compliance; Configuring and Running a Masking Job | yes |
| how does NAME_RANDOMIZE work for customer full names | NAME_RANDOMIZE | NAME_RANDOMIZE; Masking Functions Overview; ADDRESS_RANDOMIZE, IP_MASK, and NATIONAL_ID_MASK | yes |
| what parameters does EMAIL_MASK accept | EMAIL_MASK | EMAIL_MASK; What Is Data Masking; Common Masking Errors and Troubleshooting | yes |
| how should phone numbers and SSNs be masked | PHONE_MASK and SSN_MASK | GDPR and CCPA Compliance; Masking Functions Overview; PHONE_MASK and SSN_MASK | yes |
| how do CREDIT_CARD_MASK and ACCOUNT_MASK protect financial identifiers | CREDIT_CARD_MASK and ACCOUNT_MASK | CREDIT_CARD_MASK and ACCOUNT_MASK; CREDIT_CARD_MASK and ACCOUNT_MASK; Masking Functions Overview | yes |
| what does DATE_SHIFT do and does it preserve date format | DATE_SHIFT | DATE_SHIFT; Common Masking Errors and Troubleshooting; Masking Functions Overview | yes |
| how do I mask postal addresses IP addresses and national IDs | ADDRESS_RANDOMIZE, IP_MASK, and NATIONAL_ID_MASK | GDPR and CCPA Compliance; Masking Functions Overview; What Is Data Masking | no |
| how do I configure and run a masking job | Configuring and Running a Masking Job | Configuring and Running a Masking Job; Common Masking Errors and Troubleshooting; Masking Performance Tuning for Large Tables | yes |
| how do GDPR and CCPA affect data masking workflows | GDPR and CCPA Compliance | GDPR and CCPA Compliance; What Is Data Masking; Configuring and Running a Masking Job | yes |
| how can I keep customer age distribution realistic without exposing birth date | DATE_SHIFT | DATE_SHIFT; NAME_RANDOMIZE; What Is Data Masking | yes |
| mask payment identifier but keep last four digits for support lookup | CREDIT_CARD_MASK and ACCOUNT_MASK | CREDIT_CARD_MASK and ACCOUNT_MASK; CREDIT_CARD_MASK and ACCOUNT_MASK; PHONE_MASK and SSN_MASK | yes |
| developers need realistic test data but should not see real names | NAME_RANDOMIZE | NAME_RANDOMIZE; What Is Data Masking; Masking Performance Tuning for Large Tables | yes |
