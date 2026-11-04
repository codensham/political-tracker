---
name: find-evidence
description: Search for endorsements, public appearances, polls, bio entries and House disclosure filings about a candidate, and record each one with its named source. Use when asked to find any of these for a candidate.
---

# find-evidence

Argument: `<candidate-id>`. Stop and ask if it is missing or not in `data/candidates/`.

## Steps
1. Read `data/candidates/<candidate-id>.json`. Use `name`, `aliases` and the candidacy years to build search queries.
2. Search for each record type with WebSearch, using the candidate's full name and the year: endorsements ("endorses <name>"), appearances (debates, town halls, forums), polls (the pollster's own published results), bio entries (official bios and Congress.gov bioguide), and disclosures (the House Clerk index and OGE or Senate filings, through their own search pages).
3. For each hit, open the primary source: the endorser's or pollster's own page, the event page, or the news article that quotes the primary source. Use a secondary article only when the primary source is not available, and say so in the record.
4. Write one record per confirmed item, and only when the source states the fact:
   - Endorsement (`endorsement`): `endorser` (the name as the source states it), `endorser_type` (`person`, `elected_official`, `organization` or `other`), `date`.
   - Appearance (`appearance`): `event`, `venue` and `host` (null if not stated), `date`, and `transcript_url` or `video_url` (null if none).
   - Poll (`poll`): `pollster` (exactly as the pollster names itself), `value` (a percentage, 0 to 100, for the candidate), `field_start` and `field_end`, `sample` (null if not published), `population` (for example "registered voters" or "likely voters" as the pollster states it).
   - Set `source_url` to the source you opened, `published_at` to the source date, `collector` to `manual`, and `tagged_by` to `find-evidence@1`. Use `topics: []` unless the source is about a topic in `taxonomy/topics.json`.
   - Record ids: `endorsement-<cid>-<endorser slug>-<yyyy-mm-dd>`, `appearance-<cid>-<event slug>-<yyyy-mm-dd>`, `poll-<cid>-<pollster slug>-<field_end>`.
   - Bio (`bio`): `kind` (`office`, `education` or `career`), `title`, `organization`, `start_date`, `end_date` (null if ongoing), `location` (null if not stated). Id: `bio-<cid>-<slug>`.
   - Disclosure (`disclosure`): filing metadata only: `filer_name`, `year`, `form`, `filing_date`, `document_url`. Never store the filing's contents. Id: `disclosure-<cid>-<year>-<doc id>`.
5. Write each record only through `tracker.skillkit.write_checked`.
6. Run `python -m tracker.validate data`. It must exit 0.

## Rules
- Attribution only. Name the endorser or pollster as the source does. Never write a rating, a stance or a summary of the endorsement.
- Do not record a poll whose pollster or field dates you cannot confirm from the source.
- Write only under `data/endorsements/<candidate-id>/`, `data/appearances/<candidate-id>/`, `data/polls/<candidate-id>/`, `data/bio/<candidate-id>/` and `data/disclosures/<candidate-id>/`.

## Summary for the PR
For each record type: the searches run, records written (ids and source URLs), hits rejected and why, and the `validate` result.
