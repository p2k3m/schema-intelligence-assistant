# NAME_RANDOMIZE

## Usage

`NAME_RANDOMIZE` replaces a full name, first name, last name, or contact name with a realistic generated value. It is designed for `FULL_NAME` columns and person-name attributes in customer, user, employee, applicant, or patient tables.

Use this function when developers, testers, or support teams need realistic test data but should not see real names from production. The generated names keep applications usable without exposing the original person.

## Parameters

- `locale`: optional locale used for generated names.
- `preserve_initials`: when true, generated names keep the original initials.
- `deterministic`: when true, the same source value maps to the same masked value.

## Example

`Jane Doe` can become `Nisha Rao` while retaining a two-token personal-name shape.
