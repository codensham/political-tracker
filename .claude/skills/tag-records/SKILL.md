---
name: tag-records
description: Assign topic ids from the taxonomy to a candidate's untagged article, statement, bio and executive action records. Use when asked to tag or retag a candidate's records by topic.
---

# tag-records

Argument: `<candidate-id>`. Stop and ask if it is missing or not in `data/candidates/`.

## Inputs
- `data/articles/<candidate-id>/*.json` (headline, outlet), `data/statements/<candidate-id>/*.json` (quote, context), `data/bio/<candidate-id>/*.json` (title, organization) and `data/executive-actions/<candidate-id>/*.json` (title, summary of the document as the Federal Register lists it). Only records with `topics: []` are processed.
- `taxonomy/topics.json`: the only allowed topic ids. Read the list of ids and what each one covers before you tag anything.

## Steps
1. For each untagged record, read only the fields listed above. Do not fetch the source page.
2. Choose one to three topic ids that the text is clearly about. If the text is not clearly about any topic, leave `topics` empty. A weak match is not a tag.
3. Set `tagged_by` to `tag-records@1`. Change nothing else in the record.
4. Write each record only through `tracker.skillkit.write_checked`.
5. Run `python -m tracker.validate data`. It must exit 0.

## Rules
- Topics only. Do not change the quote, headline, title, dates, ids or any other field.
- Do not add a topic because the candidate's party or record suggests it. Tag from the record's own text.
- Write only under `data/articles/<candidate-id>/`, `data/statements/<candidate-id>/`, `data/bio/<candidate-id>/` and `data/executive-actions/<candidate-id>/`.

## Summary for the PR
Records tagged (id and topics), records left empty and why, and the `validate` result.
