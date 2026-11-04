---
name: backfill
description: Find gaps in a candidate's historical records (missing finance cycles, outside spending, bio entries, votes or bills for a term) and fill them from official sources. Use when asked to backfill or fill history for one candidate.
---

# backfill

Argument: `<candidate-id>`. Stop and ask if it is missing or not in `data/candidates/`.

## Steps
1. List what exists for the candidate: `data/finance/<candidate-id>/`, `data/record/<candidate-id>/`, `data/bio/<candidate-id>/`, `data/executive-actions/<candidate-id>/`, `data/disclosures/<candidate-id>/`.
2. Name the gaps. Examples: a cycle from the candidate's `candidacies` with no finance record; a congressional term with no votes; a presidential term with no executive actions; no bio entry for an office held.
3. For gaps covered by a collector, run that collector for the candidate. It is the same run as the scheduled workflow, so do not hand-edit its output:
   - Finance and outside spending: `python -m tracker.collectors fec_finance` and `python -m tracker.collectors fec_outside_spending`
   - Votes: `python -m tracker.collectors voteview`; bills: `python -m tracker.collectors congress_bills`, then `python -m tracker.tagging data`
   - Executive actions: `python -m tracker.collectors federal_register`
   - Disclosures: `python -m tracker.collectors house_clerk` (the year is set in the collector)
4. For gaps with no collector, such as a bio entry for an office or education, find an official source (the candidate's official site, a government record or an encyclopedia entry that cites one). Build a bio record and write it only through `tracker.skillkit.write_checked`. Use `kind` office, education or career, and the `start_date`/`end_date` the source gives. Leave a field null if the source does not give it.
5. Run `python -m tracker.validate data`. It must exit 0.

## Rules
- Write only under the candidate's folders in `data/finance/`, `data/record/`, `data/executive-actions/`, `data/disclosures/` and `data/bio/`.
- Collectors write official records. Skills write only judgment records, and only through `write_checked`.
- Never mark a gap as filled because a collector ran without error. Check that the record count went up, or say that it did not.

## Summary for the PR
For each gap: the action taken, records written or unchanged (collector counts), any gap left open and why, and the `validate` result.
