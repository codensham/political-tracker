# Sources and inclusion criteria

## Who is tracked

Spec §4b. A person is included if they were a **major-party presidential nominee** in an election from 2000 through 2024, or a 2028 contender added later under the same rule. Presidential candidacies only. Running mates, third-party candidates and primary runners-up are out of scope.

| Person | Candidacies |
|---|---|
| Al Gore | 2000 lost |
| George W. Bush | 2000 won, 2004 won |
| John Kerry | 2004 lost |
| Barack Obama | 2008 won, 2012 won |
| John McCain | 2008 lost |
| Mitt Romney | 2012 lost |
| Hillary Clinton | 2016 lost |
| Donald J. Trump | 2016 won, 2020 lost, 2024 won |
| Joe Biden | 2020 won, 2024 withdrew |
| Kamala Harris | 2024 lost |

Each candidacy stores its FEC candidate ID, so it can be checked at the FEC. `inclusion_reason` in `config/candidates.yaml` records the basis for each entry, and `as_of` records the date the facts were checked. Biden's 2024 candidacy is `withdrew`. Trump's 2028 eligibility is not a data field: ineligibility is a matter of record (the 22nd Amendment), not something the project asserts.

## Sources used

| Data | Source | Notes |
|---|---|---|
| Candidacies and FEC IDs | fec.gov, api.open.fec.gov | `FEC_API_KEY`; `DEMO_KEY` is the rate-limited fallback |
| Campaign finance totals | FEC API (committee totals) | Per candidate per cycle. Trump 2024 links only the "Donald J. Trump Republican Nominee Fund 2024" committee (D-038); the main committee is not yet linked |
| Outside spending | FEC API, Schedule E | Per candidate per cycle, aggregated by committee |
| Votes | Voteview | Member file gives ICPSR and Bioguide IDs; roll calls per member |
| Bills | Congress.gov API | Sponsored and cosponsored bills; policy area mapped to topics through the crosswalk |
| Executive actions | Federal Register API | Executive orders, proclamations and memoranda for presidents who held office |
| Financial disclosure metadata | House Clerk annual index | Filer name, year, form, filing date and document link only. Matched by exact name in `disclosure_names` |
| Articles | RSS and Atom feeds of the outlets in `config/outlets.yaml` | Headline and metadata only. Archive links through Wayback Save Page Now; see the archive note below |
| Official positions | Candidate platform pages | Hash, change flag and up to five verbatim key quotes. No page text. Platform URLs are not yet set for any candidate |
| Endorsements, appearances, polls | Primary sources: endorsers' own statements, event pages and transcripts, pollsters' own releases | Claude-assisted, through `find-evidence`. Attributed to the named source |
| Biographies | Official bios, Congress.gov bioguide, reference works that cite primary sources | Claude-assisted, through `backfill` |

### Outlets

Eight outlets are in `config/outlets.yaml`: NPR, The New York Times, The Wall Street Journal (World News feed), CNN, Fox News, The Hill, National Review and The Atlantic. AP (feed returned 403) and The Washington Post (feed returned 502) were dropped at build time (D-054). Lean ratings are not stored. An outlet's `rater_links` holds links to AllSides and Ad Fontes once someone verifies each page by hand (D-015). None are filled yet.

### Archive note

Wayback Save Page Now was unreachable from the build environment (D-055). Archive links are null on records collected without it. The owner must decide whether archiving is required before articles are published. This is open.

### Pollsters

No pollster list is fixed yet. A poll is added only from the pollster's own published release, with the field dates and sample it states. Pollsters are not ranked or rated by the project.

## Known gaps

Logged in [DECISIONS.md](../DECISIONS.md). Each one is a known limitation, not a silent omission. See also [COVERAGE.md](COVERAGE.md).
