# A/B Baseline Results

Rubric: 0 to 3 points per response. One point each for correct routing, grounded or safe behavior, and task-specific completeness.

Pricing is estimated from configured per-million-token rates; the local test run does not call external APIs.

| Query | Candidate A | A Score | A Latency ms | A Tokens in/out | A Estimated cost USD | Candidate B | B Score | B Latency ms | B Tokens in/out | B Estimated cost USD | Notes |
|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---|
| What does DATE_SHIFT do? | Strict grounded policy (gpt-4o-mini fallback estimate) | 2 | 1.21 | 6/84 | 0.00005130 | Loose helpful policy (Claude 3.5 Haiku fallback estimate) | 0 | 0.0 | 6/10 | 0.00004480 | grounded with citation; ungrounded or incomplete |
| What parameters does EMAIL_MASK accept? | Strict grounded policy (gpt-4o-mini fallback estimate) | 2 | 0.76 | 10/88 | 0.00005430 | Loose helpful policy (Claude 3.5 Haiku fallback estimate) | 1 | 0.0 | 10/11 | 0.00005200 | grounded with citation; ungrounded or incomplete |
| How do I comply with GDPR when masking customer data? | Strict grounded policy (gpt-4o-mini fallback estimate) | 2 | 1.27 | 14/134 | 0.00008250 | Loose helpful policy (Claude 3.5 Haiku fallback estimate) | 0 | 0.0 | 14/14 | 0.00006720 | grounded with citation; ungrounded or incomplete |
| What is the capital of France? | Strict grounded policy (gpt-4o-mini fallback estimate) | 2 | 0.0 | 8/29 | 0.00001860 | Loose helpful policy (Claude 3.5 Haiku fallback estimate) | 0 | 0.0 | 8/8 | 0.00003840 | rejected before tool use; ungrounded or incomplete |
| Mask this column: email_address | Strict grounded policy (gpt-4o-mini fallback estimate) | 1 | 0.0 | 8/25 | 0.00001620 | Loose helpful policy (Claude 3.5 Haiku fallback estimate) | 0 | 0.0 | 8/9 | 0.00004240 | asks for missing schema; ungrounded or incomplete |
