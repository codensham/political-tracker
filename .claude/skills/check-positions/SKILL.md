---
name: check-positions
description: Capture a candidate's official platform pages, compare each to its last capture, and record a position snapshot with a change flag and up to five verbatim key quotes. Use when asked to check or update a candidate's official positions.
---

# check-positions

Argument: `<candidate-id>`, and optionally the platform URLs to check. If no URLs are given, use the candidate's `official_site` from `data/candidates/<candidate-id>.json`. If there are no URLs, stop and say so.

## Steps
1. For each URL, fetch the page (HTTP GET, follow redirects). A non-200 response is a failed capture: record it in the summary and do not write a position.
2. Find the last position for this URL: the record in `data/positions/<candidate-id>/` with the latest `capture_date` and the same `url`. Take its `content_sha256` as `previous_hash`. If there is none, the capture is the first one.
3. Choose up to five key quotes from the page: short passages that state a policy position, copied character for character from the page text. Each must be 280 characters or fewer. Choose no quotes if the page has none.
4. Build the snapshot with `tracker.positions.build_position(candidate_id, url, page_text, capture_date, previous_hash=..., key_quotes=..., archive_url=None)`. It raises `KeyQuoteNotFound` if a quote is not verbatim on the page. Fix the quote and rerun. Do not drop the check.
5. Write the record only through `tracker.skillkit.write_checked`. The helper stores the hash, the change flag and the quotes. It never stores page text, so do not add any.
6. Run `python -m tracker.validate data`. It must exit 0.

## Rules
- Write only under `data/positions/<candidate-id>/`.
- `changed` is true only when the content hash differs from the previous capture. Do not judge whether the change is significant.
- Never store page text, summaries, or a statement of what the position means.

## Summary for the PR
For each URL: captured or failed (status code), `changed` value, number of key quotes, the record id, and the `validate` result.
