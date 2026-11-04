# Political Tracker — Design

Date: 2026-11-03 (revised 2026-11-04 with owner answers)
Status: Approved for build. Single source of truth. Decisions not covered here are logged in `DECISIONS.md`.

## 1. Intent

An open, git-hosted reference database of **factual, sourced information about US presidential candidates**, covering the people who ran for president from 2000 onward. A normal voter, or an AI acting for one, should be able to ask "What is X's record on Y?" and get back **evidence, not a verdict**: what the candidate did, what they said, what they officially claim, and how outlets covered it, each item dated and linked to its original source.

The repo is the product: plain JSON that anyone can read, check against the original source, and correct through git. An MCP server lets AI assistants query it with citations.

**Core principle:** the project never states a candidate's position in its own voice. It records evidence and attributes every judgment to the party that made it.

## 2. Goals

- Track every major-party presidential nominee from 2000 to 2024, plus their full political career (see §4b).
- Record only objective, sourced data (see §5). Every record has a source URL and dates.
- Collect regularly and automatically from official sources. Humans review judgment-bearing records before they land.
- Be fully open: data readable without our tooling, with git history as the audit trail.
- Provide an MCP server that answers questions with citations.
- Be a general database of candidates, not a 2028 tracker. Candidates running in 2028 are added the same way as anyone else, through a `candidacies` entry.

## 3. Non-goals (for now)

- No website or UI. Repo and MCP only.
- No non-presidential races (Senate, House, governors) as tracked candidates. The schema must not preclude them later. Congressional and state careers of tracked presidential candidates are covered as track record, not as candidacies.
- No 2028 hopefuls in this build. Adding them is a config change.
- No fact-checks, no state-legislature data (OpenStates), no GovInfo, no OpenSecrets industry data, no social-media post collection. Revisit later.
- No polling collector. Polls are added by the Claude-assisted skill from pollsters' own releases.
- No commercial use or monetization.

## 4. Anti-goals (failure even if it technically works)

- **Editorializing in our voice.** No summaries, blurbs, sentiment scores, or "X supports Y" statements authored by the project.
- **Republishing copyrighted content.** No full article text, no full third-party transcripts.
- **Invented or loaded framing.** Topic tags come only from the fixed taxonomy. Outlet lean ratings come only from named third parties, never assigned by us, and we store only a link to them (see §5).
- **Unverifiable records.** A record without a working source link is invalid.
- **Asymmetric coverage by design.** Collectors run identically for every candidate and every outlet in the config.

## 4a. Constraints (decided)

- **One reviewer** (the owner). Review load must fit one person.
- **Full political career** per candidate, not only the presidential race.
- **Zero budget.** No paid APIs or services. AI work runs inside the owner's Claude subscription (Claude Code sessions), not the paid Claude API.
- **Two review tiers.** *Official records* (FEC, Congress.gov, Voteview, Federal Register, House Clerk disclosure index) come from authoritative sources with no judgment involved. They auto-merge once CI passes. *Judgment-bearing records* (articles, quotes, topic tags, endorsements, positions, bios, polls, appearances) require the owner's approval.
- **Batched PRs:** one PR per collector run per dataset.
- **Outlets:** a fixed list of about 10 (see §5, Articles).
- **Historical backfill is gradual:** per candidate, oldest to newest, in bounded batches.
- **Corrections** update the record's source fields in place. Git history is the audit trail. There is no corrections field.
- **Secrets** live in a git-ignored `.env` at the repo root. Code reads them from the environment, falling back to `.env`. Never commit keys.

## 4b. Scope: who is tracked

Presidential candidates, 2000 to 2024. A person is included if they were a **major-party presidential nominee** in an election from 2000 through 2024, or a 2028 contender added through the same rule later. Current set (as of 2026-11-04):

| Person | Candidacies (year, result) |
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

Notes:
- Biden's 2024 candidacy is recorded as `withdrew` (he left the race in July 2024).
- Each candidacy stores its FEC candidate ID, so the candidacy can be checked at the FEC.
- Trump is no longer marked `nominee` as a status. His 2028 eligibility is not a data field. Ineligibility is a matter of record (the 22nd Amendment), not something the project asserts.
- Running-mates, third-party candidates and primary runners-up are out of scope for now.

`inclusion_reason` in `config/candidates.yaml` records the basis for each entry and where it was checked. `as_of` records the date of that check.

## 5. Data in scope (all required for MVP)

| Dataset | What it holds | Source |
|---|---|---|
| Candidates | Name, aliases, candidacies (see §6), social accounts, FEC IDs, bioguide and ICPSR IDs, official site | FEC API; Congress.gov bioguide; Voteview; candidate sites |
| Bio | One record per office held (with dates), education, and notable career entries | Official bios, Congress.gov bioguide, Miller Center, American Presidency Project, Ballotpedia. Claude-assisted, judgment tier |
| Articles | Outlet, outlet's own headline, author, published date, collected date, URL, archive URL, candidates mentioned, topic tags, extraction status, direct quotes | RSS feeds of the outlets in §5a. Matching uses the full name or a configured alias; a bare surname never matches |
| Statements / quotes | Verbatim quote, speaker (must be the candidate), date, venue or context, source URL, archive URL, topic tags | Articles, official transcripts, candidate sites, Commission on Presidential Debates. Claude-assisted, judgment tier |
| Official positions | Per platform page: URL, capture date, Wayback snapshot link, content hash, changed-since-last-capture flag, short verbatim quotes of key lines. No full page text | Candidate sites and Wayback snapshots (campaign pages where they exist) |
| Track record | Congressional votes (Voteview), bills sponsored and co-sponsored (Congress.gov), executive actions (Federal Register: executive orders, proclamations, memoranda) for those who held office | Voteview, Congress.gov, Federal Register, Miller Center |
| Campaign finance | Totals per cycle (receipts, disbursements, cash on hand, debts), principal committee where the candidate has one. Outside spending (independent expenditures, Schedule E) per candidate per cycle | FEC API |
| Personal finances | Filing metadata only: filer, year, form, filing date, document link | House Clerk annual disclosure index (official tier). OGE Form 278e and Senate eFD through the Claude-assisted skill (judgment tier) |
| Endorsements | Endorser, date, source URL | Articles, candidate sites. Claude-assisted |
| Polling | Poll value, pollster, field dates, sample, source URL, attributed to the pollster | Pollsters' own releases. Claude-assisted. No automated scraping |
| Media attention | Derived counts: articles per candidate per outlet per period | Computed from Articles when queried, not stored |
| Appearances | Debates, interviews, rallies: date, venue, host, transcript or video link | Commission on Presidential Debates, networks, C-SPAN, candidate sites. Claude-assisted |

**Position timeline** is not a separate dataset. It is a query over quotes, official positions, votes and bills, filtered by candidate and topic and sorted by date.

### 5a. Outlets

About 10 outlets, fixed in `config/outlets.yaml`: AP, NPR, New York Times, Wall Street Journal, Washington Post, CNN, Fox News, The Hill, National Review, The Atlantic. Any outlet without a working RSS feed at build time is dropped and the reason logged in `DECISIONS.md`.

### Content rules

- Store metadata, the outlet's headline, and **short verbatim quotes** only. Never full article or transcript text.
- Collectors may fetch full text transiently to extract quotes and tags. That text is not committed.
- Each article gets an archive link (anonymous Wayback Save Page Now, rate-limited, with retries) at collection time. If archiving fails, `archive_url` is null and the record stays valid.
- Government records (votes, bills, FEC data, executive actions, official transcripts) are public domain and may be stored in fuller form.
- Every quote must appear verbatim in its linked source. CI checks new or changed quotes (see §6).
- **Statements hold only the candidate's own words**, including official campaign accounts. Quotes from surrogates, opponents or officials stay on the article record and are never returned as the candidate's evidence.
- Collectors send a User-Agent of `political-tracker (+https://github.com/codensham/political-tracker)`, with no email address.

### Topic tagging

- Tags are suggested automatically (keyword or Claude-assisted), confirmed by the reviewer where judgment is involved, and every record stores how it was tagged (`tagged_by`: method and version, or reviewer).
- **Policy-area crosswalk:** Congress.gov assigns each bill one official policy area (for example "Health"). `taxonomy/policy_area_crosswalk.json` is a published, versioned mapping from those policy areas to our topic IDs. Bills and votes linked to a bill receive topics through it (`tagged_by: crosswalk@1`) without manual review. Changes to the crosswalk itself go through a PR with a stated reason.
- Executive actions are tagged through the Claude-assisted tagging skill and need review.

### Neutrality metadata

- **Outlet lean:** the rating is not stored. Each outlet record stores a link to the rater's page (AllSides, Ad Fontes) and the date the link was checked, so the value is never reproduced.
- **Topic taxonomy:** a fixed, versioned list in `taxonomy/topics.json`: economy, taxes, healthcare, immigration, foreign-policy, defense, climate-energy, environment, guns, abortion, criminal-justice, education, civil-rights, labor, trade, technology, elections-democracy, government-ethics, housing, agriculture. Changes go through a PR with a stated rationale.

## 6. Architecture

```
sources ──► collectors (scheduled) ──► pull requests ──► human review + CI validation ──► main
                                                                                        │
                                                         MCP server (reads JSON) ◄──────┘
```

### Language and tooling

- **Python 3.12** for collectors and MCP server (CI runs 3.12; local development may use any 3.12+).
- **JSON files in git** as the database, one file per record, validated by **JSON Schema** (draft 2020-12).
- **GitHub** for hosting and PR review; **GitHub Actions** for scheduled collection and CI.
- **MCP** server on the official Python MCP SDK (FastMCP), stdio transport.
- **ruff** for linting and formatting checks, run in CI.

### Candidate record (revised)

- `name`, `aliases` (list; used for article matching), `social_accounts` (list of `{platform, handle, url}`), `candidacies`, `icpsr`, `bioguide_id`, `official_site`, `inclusion_reason`.
- `candidacies`: list of `{office: "president", year, party, result, fec_candidate_id, source_url}`. `result` ∈ `potential | declared | withdrew | nominee | won | lost`. A candidacy with a future year and `potential` or `declared` is a current contender.
- The top-level `status` and `party` fields are removed. They are replaced by `candidacies`.
- `list_candidates` filters by `office`, `year` or `result`.

### Repository layout

```
data/
  candidates/<candidate-id>.json
  bio/<candidate-id>/<id>.json
  articles/<candidate-id>/<id>.json       # yyyy/mm is in published_at, not in the path
  statements/<candidate-id>/<id>.json
  positions/<candidate-id>/<id>.json      # one per capture
  record/<candidate-id>/<id>.json         # votes, bills
  executive-actions/<candidate-id>/<id>.json
  finance/<candidate-id>/<id>.json        # totals and outside spending
  disclosures/<candidate-id>/<id>.json
  endorsements/<candidate-id>/<id>.json
  polls/<candidate-id>/<id>.json
  appearances/<candidate-id>/<id>.json
taxonomy/topics.json
taxonomy/policy_area_crosswalk.json
schemas/*.schema.json
src/tracker/...                           # collectors, validator, MCP server, skill helpers
config/candidates.yaml, config/outlets.yaml
docs/ (NEUTRALITY.md, CONTRIBUTING.md, SOURCES.md, CORRECTIONS.md)
.claude/skills/                           # the five Claude-assisted skills
```

Non-candidate records are stored under the folder of their first candidate ID (`record_path` in `src/tracker/records.py`). That function is the canonical layout.

Every record carries at minimum: `id`, `type`, `candidate_ids`, `source_url`, `published_at`, `collected_at`, `collector`, `topics`. Optional: `archive_url`, `tagged_by`.

### Two kinds of collectors

1. **Deterministic collectors (GitHub Actions).** Plain Python, no AI. FEC totals and outside spending, Congress.gov bills, Voteview votes, Federal Register executive actions, House Clerk disclosure index, outlet RSS feeds, Wayback archiving. They produce records from metadata and government data.
2. **Claude-assisted skills (run by the owner in Claude Code sessions).** Five skills in `.claude/skills/`, each taking a candidate ID as an argument. They do not multiply per candidate.
   - `extract-quotes-tags`: works through articles with `extraction_status: pending`, producing statements and tags.
   - `backfill`: candidate plus date range, finds articles through GDELT, outlet sitemaps and Wayback CDX, then runs extraction.
   - `check-positions`: fetches campaign platform pages, records hash and change flag, extracts key quotes.
   - `find-evidence`: candidate plus type (`bio`, `endorsement`, `appearance`, `poll`, `disclosure`), gathering records with sources.
   - `tag-records`: suggests topics for untagged records (executive actions and similar), for review.

   Each skill writes through a tested helper that validates records and refuses any record with a stance field.

### Collection and review

- Each collector runs on a schedule, normalizes items into records, deduplicates against existing data, and opens or updates a PR. It never commits to `main`.
- Manual contributions use the same schemas and PR path.
- **CI on every PR:** tests, schema validation, taxonomy check, duplicate detection, ruff. For new or changed records only: link reachability (a 404 blocks; 403, paywall or timeout is a warning) and quote verification (the quote must appear verbatim in the re-fetched source; if the source cannot be fetched, the quote is flagged for the reviewer).
- Official-record PRs auto-merge on green CI. Judgment-bearing PRs need the owner's approval.
- **Collector failures:** every collector runs even if an earlier one fails. The PR contains whatever succeeded. The workflow fails at the end if any collector failed.
- Schedules: official records daily; RSS daily (one batched PR on `collect/articles`); Claude-assisted skills on demand.

### MCP server

Read-only over the JSON data. Runs locally (stdio) from a cloned copy of the repo.

Tools:
- `list_candidates(office?, year?, result?)`
- `get_candidate(candidate)`: name, aliases, candidacies, IDs, links
- `search_evidence(candidate, topic?, date_from?, date_to?, types?, limit=50)`: statements, positions, votes, bills, executive actions, articles, endorsements, appearances, polls
- `position_timeline(candidate, topic)`: evidence on a topic, sorted by date
- `get_finance(candidate, cycle?)`, `get_outside_spending(candidate, cycle?)`
- `get_disclosures(candidate)`, `get_bio(candidate)`
- `get_endorsements(candidate)`, `get_appearances(candidate)`, `get_polls(candidate)`
- `media_attention(candidate?, outlet?, period?)`: computed on each call
- `compare(candidates[], topic)`: side-by-side evidence, no ranking

Every result has `results`, `count`, `truncated`, `note`. Every record in it has `source_url`. The server returns evidence only and adds no characterization of its own. Unknown candidate IDs return an error that lists the valid IDs.

Performance: records are loaded into memory at startup. If startup exceeds 5 seconds, a SQLite cache built from the JSON is added. The JSON stays canonical.

## 7. Build order

1. Candidate model v2, then seed the 2000–2024 nominees
2. Finance: fix Trump 2024 totals, add outside spending
3. Executive actions for presidents who held office
4. Congress.gov bills, policy-area crosswalk, vote topics
5. Bio records
6. Outlets, RSS articles, archiving, statements and CI quote and link checks
7. Official positions snapshots
8. Endorsements, appearances, polls schemas
9. Disclosures (House Clerk index)
10. Media attention and full MCP toolset
11. Claude-assisted skills and their helpers
12. CI hardening, docs, final spec audit

The MVP is complete when every dataset in §5 has a schema, a collector or skill, tests, an MCP tool, and at least one real record per tracked candidate where data exists. Historical backfill beyond the initial sample is ongoing operation, not build scope.

## 8. Licensing and governance

- Code: MIT. Data we author (structure, tags, compiled records): CC BY 4.0. Third-party content (quotes, headlines) remains its owners'. We rely on short attributed excerpts.
- `docs/NEUTRALITY.md` states the rules in §4 and §5 and is the standard reviewers enforce.
- Respect source terms of service and robots.txt. Prefer official APIs and RSS over scraping.

## 9. Resolved decisions

All former open questions were answered on 2026-11-04. The answers are recorded in `DECISIONS.md` (D-001 to D-030). Anything the build decides beyond those answers is logged there too.
