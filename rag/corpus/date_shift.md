# DATE_SHIFT

## Usage

`DATE_SHIFT` moves a date by an offset while preserving a valid date and the original date format. Use it for `DATE_OF_BIRTH` or other personal dates when age or interval relationships must remain realistic without exposing the original value.

## Parameters

- `min_days`: minimum shift offset.
- `max_days`: maximum shift offset.
- `preserve_weekday`: keeps the shifted date on the same weekday.
- `preserve_relative_distance`: applies the same offset to related dates for one subject.

## Example

`1980-04-02` can shift to `1980-05-17`. The output remains a date, and format preservation keeps integrations stable.

