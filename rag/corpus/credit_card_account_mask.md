# CREDIT_CARD_MASK and ACCOUNT_MASK

## CREDIT_CARD_MASK

`CREDIT_CARD_MASK` protects payment card numbers and should preserve only the minimum digits needed for support or reconciliation. It validates format and can keep the last four digits.

Parameters include `preserve_last4`, `preserve_card_brand`, and `deterministic`.

## ACCOUNT_MASK

`ACCOUNT_MASK` protects bank, customer, and billing account numbers. Use it for `ACCOUNT_NUMBER` columns such as `cust_acct_no`, `account_number`, `iban`, and `bank_account`.

Parameters include `preserve_last4`, `prefix_strategy`, and `deterministic`.

## Example

`ACC-98765` can become `ACC-*****` while keeping the account prefix recognizable.

