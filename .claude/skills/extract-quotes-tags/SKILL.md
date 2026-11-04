---
name: extract-quotes-tags
description: Extract a candidate's own verbatim quotes from their article source pages and write them as statement records with topics. Use when asked to pull statements for a candidate from the articles in data/articles/<candidate-id>/.
---

# extract-quotes-tags

Argument: `<candidate-id>` (for example `donald-trump`). Stop and ask if it is missing or not in `data/candidates/`.

## Inputs
- `data/articles/<candidate-id>/*.json`: article records. Only `extraction_status: "pending"` ones are processed.
- Each article's `source_url` page, fetched at run time. Page text is never written to disk.
- `data/candidates/<candidate-id>.json`: `name` and `aliases`. The speaker must equal one of them (D-037).
- `taxonomy/topics.json`: the only allowed topic ids.

## Steps
1. For each pending article, fetch `source_url`. If the fetch fails with a 4xx or 5xx, leave the article pending and note the URL in the summary.
2. Find sentences where the candidate speaks in their own words: direct quotes or quoted remarks attributed to them. Copy each one character for character. Keep it at 280 characters or fewer. Skip paraphrase, reporter narration and other people's words.
3. For each quote, build a statement record:
   - `id`: `statement-<candidate-id>-<yyyy-mm-dd>-<first 8 hex of sha256(quote)>`, where the date is the day the candidate said it, or the article date if the source does not say.
   - `type`: `statement`; `candidate_ids`: `[<candidate-id>]`; `source_url`: the article URL.
   - `published_at`: the date the candidate said it, or the article date.
   - `collector`: `manual`; `collected_at`: current UTC time; `tagged_by`: `extract-quotes-tags@1`.
   - `quote`, `speaker` (the name or alias as the article prints it), `venue`, `context` (one short line or null), `archive_url` (null unless you have one).
   - `topics`: one to three ids from `taxonomy/topics.json`. If nothing fits, use `[]`.
4. Write each statement and the updated article (set `extraction_status` to `"done"`) only through `tracker.skillkit.write_checked`. Never write a file directly.
5. Check the quotes: `python -m tracker.checks --data data` must show no errors for the records you wrote.
6. Run `python -m tracker.validate data`. It must exit 0.

## Rules
- Write only under `data/statements/<candidate-id>/` and `data/articles/<candidate-id>/`.
- No stance, sentiment, summary or verdict fields. Do not characterize what the candidate meant.
- Do not store article text. Store only the quote.

## Summary for the PR
List the articles processed, statements written (ids), articles skipped and why, and the `checks` and `validate` results.
