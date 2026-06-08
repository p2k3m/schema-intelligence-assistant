# ADDRESS_RANDOMIZE, IP_MASK, and NATIONAL_ID_MASK

## ADDRESS_RANDOMIZE

`ADDRESS_RANDOMIZE` replaces street, postal, city, and region values with plausible address data. Use it for `ADDRESS` columns such as `shipping_address`, `home_address`, and `address_line_1`.

## IP_MASK

`IP_MASK` hides host-level network identifiers. It supports full redaction or subnet-preserving masks for analytics on traffic volume by network.

## NATIONAL_ID_MASK

`NATIONAL_ID_MASK` protects government identifiers such as national insurance numbers, Aadhaar numbers, passport numbers, driver license numbers, and tax IDs.

## Example

`192.168.1.22` can become `192.168.1.0` with subnet preservation, while a national ID can keep only an approved suffix.

