# Customer Value

## Baseline Problem

Enterprise onboarding teams spend days reviewing database schemas to find PII and hand-write masking rules. The pain is not just effort: missed PII can create compliance risk, while inconsistent manual rules slow every new customer environment.

## Measurable Outcome

In a 30-day pilot with 3 customers, I would measure:

- Time from schema connection to first masking configuration, target: reduce from 3-4 days to under 2 hours.
- PII recall on customer-reviewed columns, target: 95 percent after human adjudication feedback.
- Review queue size, target: fewer than 25 percent of detected PII columns requiring manual review.
- Masking rule acceptance rate, target: 80 percent of high-confidence generated rules accepted without edits.
- Professional services hours saved per onboarding, target: at least 16 hours per customer.

## Risks and Limitations

The system can miss obfuscated or domain-specific PII, confuse business identifiers with personal identifiers, or recommend a technically valid masking function that violates a customer policy. Guardrails include recall-oriented thresholds, explicit confidence scores, a review queue for uncertain columns, golden-set regression tests, grounded documentation answers, and out-of-scope refusal.

## What Should Stay Human

Humans should approve low-confidence detections, customer-specific policy exceptions, production rollout timing, and any rule that preserves original characters from regulated identifiers. Compliance ownership should remain with the customer and data governance team; the assistant should accelerate review, not silently become the policy authority.

