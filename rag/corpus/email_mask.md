# EMAIL_MASK

## Usage

`EMAIL_MASK` masks an email address by replacing the mailbox portion and optionally preserving the domain. Use it for `EMAIL` columns such as `email_address`, `contact_email`, and non-English aliases like `correo_electronico`.

## Parameters

- `preserve_domain`: keeps the original domain, such as `example.com`.
- `domain_strategy`: `preserve`, `fixed`, or `randomized`.
- `deterministic`: maps the same email to the same masked email.

## Example

`alex.chen@example.com` can become `user_4821@example.com` when domain preservation is enabled.

