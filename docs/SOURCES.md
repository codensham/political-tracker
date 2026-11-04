# Sources and inclusion criteria

## Who is tracked

A person is included in the 2028 presidential tracker if either:

1. **(a) Filed.** They filed FEC Form 2 (Statement of Candidacy) for the 2028 presidential race. Source: FEC candidate search, `office=P`, `election_year=2028`.
2. **(b) Polling.** They have not filed, but appear in at least two named national primary polls at 2% or higher. Source: the named polls, cited by URL.

`inclusion_reason` in `config/candidates.yaml` records which criterion applies and where it was checked. `as_of` records the date of that check.

Owner's call (spec §9). Revisit if the criteria produce too many or too few names.

## Sources used

| Data | Source | Notes |
|---|---|---|
| FEC candidate IDs and filings | https://www.fec.gov (API: https://api.open.fec.gov/v1/) | Free key via api.data.gov; `DEMO_KEY` works for light use |
| Congressional ICPSR and Bioguide IDs | Voteview member file; Congress.gov bioguide | Used for votes; null if no congressional career |
| Primary polling (criterion b) | Named pollsters or aggregators, cited by URL in `inclusion_reason` | Source choice pending owner review |
