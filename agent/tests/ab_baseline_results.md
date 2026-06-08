# A/B Baseline Results

Rubric: 0 to 3 points per response. One point each for correct routing, grounded or safe behavior, and task-specific completeness. Baseline B is a reserved future model slot.

| Query | Baseline A | Baseline B | Notes |
|---|---:|---:|---|
| What does DATE_SHIFT do? | 2 | 0 | grounded with citation |
| What parameters does EMAIL_MASK accept? | 2 | 0 | grounded with citation |
| How do I comply with GDPR when masking customer data? | 1 | 0 | grounded with citation |
| What is the capital of France? | 2 | 0 | rejected out-of-scope query |
| Mask this column: email_address | 2 | 0 | asked for missing schema |
