# PHONE_MASK and SSN_MASK

## PHONE_MASK

`PHONE_MASK` replaces subscriber digits while keeping country code and formatting when possible. Use it for `PHONE` columns such as `phone_number`, `mobile_phone`, `telephone`, and `msisdn`.

Parameters include `preserve_country_code`, `preserve_format`, and `deterministic`.

## SSN_MASK

`SSN_MASK` protects US Social Security numbers. It can preserve the last four digits for support workflows or mask all digits for stricter environments.

Parameters include `preserve_last4`, `preserve_format`, and `deterministic`.

## Example

`123-45-6789` can become `***-**-6789` or `***-**-****` based on policy.

