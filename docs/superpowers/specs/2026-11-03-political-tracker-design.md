# Political Tracker — Design

Date: 2026-11-03
Status: Draft, awaiting approval

## 1. Intent

An open-source, git-hosted reference index of **factual, sourced information about US presidential candidates**, starting with the 2028 cycle. A normal voter — or an AI acting for one — should be able to ask "What is X's stance on Y?" and get back **evidence, not a verdict**: what the candidate said, what they did, what they officially claim, and how outlets covered it, each item dated and linked to its original source.

The repo itself is the product: a "glossary" anyone can point a human or an AI at to find voting-relevant information and verify it at the source. An MCP server lets AI assistants query it directly.

**Core principle:** the project never states a candidate's position in its own voice. It records evidence and attributes every judgment to the party that made it.

## 2. Goals

- Cover major 2028 US presidential candidates: likely contenders now, marked `declared` when they officially announce, archived if they don't run.
- Record only objective, sourced data (see §5). Every record has a source URL and dates.
- Aggregate regularly and automatically from sources, with humans reviewing before anything lands.
- Be fully open: data readable without any of our tooling (plain JSON in git), with git history as the public audit trail.
- Provide an MCP server that answers questions with citations.

## 3. Non-goals (for now)

- No website / UI. Repo + MCP only.
- No coverage of non-presidential races (Senate, House, governors) yet. The schema should not preclude adding them later.
- No commercial use or monetization.

## 4. Anti-goals (failure even if it technically works)

- **Editorializing in our voice.** No summaries/blurbs, no sentiment scores, no "X supports Y" statements authored by the project.
- **Republishing copyrighted content.** No full article text, no full third-party transcripts. Attribution does not make this legal; takedowns would get the repo removed.
- **Invented or loaded framing.** Topic tags come only from a fixed, published taxonomy. Outlet lean ratings come only from named third parties, never assigned by us.
- **Unverifiable records.** Any record without a working source link (or archive link) is invalid.
- **Asymmetric coverage by design.** Collectors must run identically for every candidate and every outlet in the configured lists.

## 4a. Constraints (decided)

- **One reviewer** (the owner) for now. Review load must be designed to fit one person.
- **Full political career** history per candidate, not just the 2028 cycle.
- **Zero budget.** No paid APIs or services. AI work runs inside the owner's existing Claude subscription (Claude Code sessions), not the paid Claude API.

Consequences, built into the design below:
- **Two review tiers.** *Official records* (FEC, Congress.gov/Voteview votes and bills, disclosure filing metadata) come from authoritative APIs with no judgment involved; they auto-merge once CI passes. *Judgment-bearing records* (articles, quotes, topic tags, endorsements, positions) require the owner's approval.
- **Batched PRs:** one PR per collector run per dataset, so review is a daily/weekly sweep, not hundreds of PRs.
- **Start with a small outlet list** (roughly 8–10, balanced across third-party lean ratings) and grow as review capacity allows.
- **Historical backfill is gradual:** run per candidate, oldest-to-newest, in bounded batches, rather than all at once.

## 5. Data in scope (all required for MVP)

| Dataset | What it holds | Likely sources (builder to confirm) |
|---|---|---|
| Candidates | Name, party, status (`potential`/`declared`/`withdrawn`/`nominee`), FEC ID, official site, social accounts | FEC, candidate sites |
| Bio | Offices held (with dates), education, career | Official bios, Congress bioguide, state sources |
| Articles | Outlet, headline (outlet's own), author, published date, collected date, URL, archive URL, candidates mentioned, topic tags, direct quotes | Outlet RSS feeds |
| Statements / quotes | Verbatim quote, speaker, date, venue/context, source URL, topic tags | Articles, official transcripts, candidate sites, social posts |
| Official positions | Per platform page: URL, capture date, Wayback snapshot link, content hash, detected-change flag, and short verbatim quotes of key lines. No full page text (campaign sites are copyrighted) | Candidate websites (+ Wayback snapshots) |
| Track record | Votes, bills sponsored/co-sponsored, executive actions (for those who held office) | Congress.gov API, House/Senate roll calls, state legislature/governor records |
| Campaign finance | Fundraising totals, cash on hand, top donor industries, outside/PAC spending | FEC API; OpenSecrets for industry rollups (check terms) |
| Personal finances | MVP: filing metadata (filer, year, form, filing date) + document link. Parsing asset ranges/holdings into structured data is post-MVP | OGE Form 278e via FEC, House Clerk / Senate eFD |
| Endorsements | Endorser, date, source | Articles, candidate sites |
| Fact-checks | Claim, rating, checker, date, URL — attributed as the checker's judgment | Google Fact Check Tools API (ClaimReview), PolitiFact, FactCheck.org |
| Polling | Poll/average value, pollster/aggregator, field dates, sample, URL — attributed | Named pollsters/aggregators (builder to pick stable sources) |
| Media attention | Derived counts: articles per candidate per outlet per period | Computed from Articles dataset |
| Appearances | Debates, interviews, rallies: date, venue, host, transcript/video link | Debate commissions, networks, C-SPAN, candidate sites |

**Position timeline** is not a separate dataset: it is a query over quotes, official positions and track record filtered by candidate + topic and sorted by date. Shifts become visible without us declaring them.

### Content rules

- Store metadata, the outlet's headline, and **short verbatim quotes** only. Never full article or transcript text.
- Collectors may fetch full text transiently to extract quotes and tags; that text is not committed.
- Each article gets an archive link (Wayback Machine Save Page Now) at collection time.
- Government-produced records (votes, bills, FEC data, official transcripts) are public domain and may be stored in fuller form.
- Every quote must appear verbatim in its linked source; review checks this.
- **Statements hold only the candidate's own words** (including official campaign accounts). Quotes from surrogates, opponents or officials may stay on the article record but are never returned as that candidate's evidence.

### Topic tagging (my call)

- Tags are suggested automatically (AI or keyword), confirmed by the human reviewer, and every record stores how it was tagged (`tagged_by`: method + version, or reviewer).
- Votes and bills carry Congress.gov's official policy-area/subject terms as well as our taxonomy tags, mapped by a published crosswalk.

### Neutrality metadata

- **Outlet lean:** stored per outlet with the rating's source named (e.g. AllSides, Ad Fontes) and retrieval date. Multiple raters allowed. Builder must check those raters' terms of reuse; if reuse isn't allowed, store a link to the rating instead of the value.
- **Topic taxonomy:** a fixed, versioned list in the repo (e.g. economy, healthcare, immigration, foreign policy, climate/energy, guns, abortion, criminal justice, education, …). Changes go through a PR with a stated rationale.

## 6. Architecture

```
sources ──► collectors (scheduled) ──► pull requests ──► human review + CI validation ──► main
                                                                                        │
                                                         MCP server (reads JSON) ◄──────┘
```

### Language and tooling (my call)

- **Python** for collectors and MCP server.
- **JSON files in git** as the database, one file per record, validated by **JSON Schema**.
- **GitHub** for hosting, PR review, and **GitHub Actions** for scheduled collection and CI.
- MCP server built on the official Python MCP SDK.

### Repository layout (sketch — builder may refine)

```
data/
  candidates/<candidate-id>.json
  outlets/<outlet-id>.json          # incl. attributed lean ratings
  articles/<yyyy>/<mm>/<id>.json
  statements/<candidate-id>/<id>.json
  positions/<candidate-id>/<capture-date>.json
  record/<candidate-id>/<id>.json   # votes, bills, exec actions
  finance/<candidate-id>/<period>.json
  disclosures/<candidate-id>/<year>.json
  endorsements/<candidate-id>/<id>.json
  factchecks/<candidate-id>/<id>.json
  polls/<id>.json
  appearances/<candidate-id>/<id>.json
taxonomy/topics.json
schemas/*.schema.json
collectors/<source>/...
mcp_server/
config/candidates.yaml, config/outlets.yaml   # what to collect
docs/  (NEUTRALITY.md, CONTRIBUTING.md, SOURCES.md, CORRECTIONS.md)
```

Every record carries at minimum: `id`, `type`, `candidate_ids`, `source_url`, `archive_url` (where applicable), `published_at`, `collected_at`, `collector` (name+version or `manual`), `topics`.

### Two kinds of collectors

1. **Deterministic collectors (GitHub Actions, free for public repos).** Plain Python, no AI. Official APIs (FEC, Congress.gov), bulk historical votes (Voteview, free CSV of every congressional roll call), outlet RSS feeds, disclosure filing indexes, Wayback archiving, fact-check APIs (Google Fact Check Tools, free key). These produce raw records with metadata only.
2. **Claude-assisted collectors (run by the owner in Claude Code sessions).** Repo-provided Claude Code skills/commands, e.g. "extract quotes and tags for pending articles", "backfill candidate X, 2012–2014", "check campaign pages for changes", "find endorsements". Claude reads sources (via its web/browser tools), writes records in the schema, and opens a PR for review. Can be scheduled with Claude Code's local scheduled tasks when the owner's machine is on. Bounded by subscription usage limits, so these run in batches.

Historical articles have no RSS: backfill uses free indexes (GDELT, outlet sitemaps, Wayback CDX) to find URLs, then Claude-assisted extraction.

**Social posts:** X's API is paid and most platforms forbid scraping, so social posts are limited to what's quoted in articles or posted on candidate sites for MVP. Revisit later.

### Collection and review

- Each collector runs on a schedule, normalizes items into records, deduplicates against existing data, and opens (or updates) a PR — never commits directly to `main`.
- Manual contributions use the same schemas and the same PR path.
- CI on every PR: schema validation, taxonomy check, link reachability, duplicate detection.
- Official-record PRs auto-merge on green CI; judgment-bearing PRs need the owner's approval (see §4a). Quote verification: CI re-fetches the source and checks the quote appears verbatim where possible; the reviewer spot-checks the rest.
- Corrections: anyone can open an issue/PR; corrections preserve history (git) and are noted on the record.

### MCP server

Read-only over the JSON data. Runs locally (stdio) from a cloned copy of the repo; a hosted endpoint is post-MVP (my call). Tools along the lines of:
- `list_candidates(status?)`
- `get_candidate(candidate)` — bio, status, links
- `search_evidence(candidate, topic?, date_from?, date_to?, types?)` — quotes, positions, record items
- `position_timeline(candidate, topic)` — evidence sorted by date
- `get_finance(candidate, period?)`, `get_disclosures(candidate)`
- `get_endorsements`, `get_factchecks`, `get_polls`, `get_appearances`, `media_attention(candidate?, outlet?, period?)`
- `compare(candidates[], topic)` — side-by-side evidence, no ranking

Every result includes source URLs and dates. The server returns evidence only; it adds no characterization of its own.

## 7. Build order (my call)

Schemas for all datasets come first. Collectors then land in value order: candidates + bio → track record + FEC finance → articles + quotes → official positions → disclosures → endorsements → fact-checks → polling → appearances → media attention (derived). MCP server can start once the first datasets exist. MVP is complete when all are in.

## 8. Licensing and governance (my calls)

- Code: MIT. Data we author (structure, tags, compiled records): CC BY 4.0. Third-party content (quotes, headlines) remains its owners'; we rely on short attributed excerpts.
- `NEUTRALITY.md` states the rules in §4–5 and is the standard reviewers enforce.
- Respect source terms of service and robots.txt; prefer official APIs and RSS over scraping.

## 9. Left to the builder

- Exact JSON schemas and ID formats.
- Specific outlet list for RSS (aim: broad spread across the lean spectrum per third-party ratings).
- Choice of polling and fact-check sources given API availability and terms.
- Exact prompts/skills for the Claude-assisted collectors (human review required before merge).
- Deduplication strategy, scheduling frequency, rate limiting.
- MCP search implementation (in-memory index, SQLite built from JSON, etc.).
- Initial list of potential 2028 candidates, with inclusion criteria documented (e.g. FEC filing, major-outlet coverage threshold).
