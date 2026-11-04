# Build plan

Source of truth for scope: `docs/superpowers/specs/2026-11-03-political-tracker-design.md`. Decisions: `DECISIONS.md`.

Rules: TDD. Each phase ends with its acceptance criteria met and `python scripts/verify.py` exiting 0. Commit after each phase. Check boxes as work completes.

## Phase 0 — Baseline, tooling, secrets

- [x] Foundation (old plan Tasks 1–8) built and merged: records I/O, schemas, validator, candidate sync, collector runner, FEC, Voteview, MCP server, CI, docs. 76 tests pass at baseline.
- [x] Federal Register executive actions collector (`federal_register`) and its tests.
- [x] Add `ruff` to `[project.optional-dependencies] dev` and a `[tool.ruff]` config in `pyproject.toml`. Run and fix until `ruff check .` and `ruff format --check .` are clean. (D-040)
- [x] `src/tracker/config.py`: `get_key(name) -> str | None` reads `os.environ`, then `.env` at repo root. Parser: `KEY=value`, skips comments and blank values, strips quotes. Blank means unset.
  - Tests: env beats file; blank in file → None; comments ignored; missing `.env` → None; FEC collector uses the key and falls back to `DEMO_KEY`.
- [x] `scripts/verify.py`: runs `ruff check`, `ruff format --check`, `pytest`, `tracker.validate data`. Exits non-zero on the first failure, prints which step failed. (D-039)
  - Tests: `tests/test_verify.py` runs it with steps stubbed and checks exit codes.
- [x] Copy `.env` into this worktree root (git-ignored). Confirm `get_key("FEC_API_KEY")` returns a value without printing it.

**Acceptance:** `python scripts/verify.py` exits 0. No key value appears in any output or file.

## Phase 1 — Candidate model v2

- [x] `schemas/candidate.schema.json`: remove `status`, `party`. Add `aliases` (array of strings, minItems 1), `social_accounts` (array of `{platform, handle, url}`), `candidacies` (array of `{office: "president", year: int, party, result, fec_candidate_id: string|null, source_url: uri}`, `result` ∈ `potential|declared|withdrew|nominee|won|lost`).
- [x] Migrate `data/candidates/donald-trump.json` and `config/candidates.yaml` to the v2 shape. Trump: candidacies 2016 won, 2020 lost, 2024 won. Remove `status`.
- [x] `candidates.py`: `_build` maps config fields to v2. `status` and `party` in config are rejected with a clear error (not silently dropped).
- [x] `mcp_server/index.py`: `candidates(office, year, result)` filters replace `status`.
  - Tests:
    - a candidacy with an unknown `result` fails validation
    - a candidate with no `aliases` fails
    - a candidate with top-level `status` fails
    - sync is idempotent (second run writes 0)
    - `list_candidates` filters by `result` and `year`
    - Trump has 3 candidacies with the expected results

**Acceptance:** validator clean; existing tests updated, not deleted; spec §6 matches the schema.

## Phase 2 — Seed the 2000–2024 nominees, and fix Trump's 2024 finance

- [x] Research FEC candidate IDs and principal committees for the 10 people in spec §4b. Record sources in `docs/SOURCES.md`.
- [x] Add 10 entries to `config/candidates.yaml` with `aliases`, `candidacies`, `inclusion_reason`, `as_of`.
- [x] Investigate Trump 2024 receipts (`$29,133.95`). Compare candidate-level totals with the principal committee's totals on the FEC API. If principal committee is the cause, the finance collector queries committee totals for candidates with a committee, and the fix is tested. Log the finding as D-038.
  - Tests: fixture of committee totals → mapped record; regression test that the Trump 2024 fixture yields the principal committee's receipts.
- [x] Run the sync and the finance collector for all 10. Commit the data.

**Acceptance:** 10 candidate records validate. Every candidacy has an FEC ID or a `null` with a reason in `inclusion_reason`. Finance records for each candidate for each cycle they filed. D-038 written.

## Phase 3 — Outside spending (FEC Schedule E)

- [x] Schema `schemas/outside_spending.schema.json`: `type: "outside_spending"`, `cycle`, `support_oppose` ∈ `support|oppose`, `amount`, `committee_id`, `committee_name`, `coverage_start`, `coverage_end`, `fec_candidate_id`. Folder `data/finance/<cid>/`.
- [x] `collectors/fec_outside_spending.py` (`name = "fec_outside_spending"`): Schedule E independent expenditures by candidate per cycle, paginated, retries via `get_json`.
  - Tests: mapping from fixture; pagination follows `pagination.last_indexes`; 429 retried; candidate without FEC IDs skipped; rerun unchanged → 0 writes.
- [x] Register in `BUILTIN_MODULES` and add to `collect-official.yml`.

**Acceptance:** collector runs against fixtures; validator clean on its output; workflow lists it.

## Phase 4 — Executive actions for presidents who held office

- [x] Confirm Federal Register president slugs for Bush, Obama, Trump, Biden against the API. Add to `PRESIDENT_SLUGS`.
- [x] Tests: each slug in the map yields records from a fixture; a non-holder (for example Gore) yields none.
- [x] Run and commit the data.

**Acceptance:** each president who held office has records; validator clean; D-035 holds.

## Phase 5 — Congress.gov bills and the policy-area crosswalk

- [x] Schema `schemas/bill.schema.json`: `type: "bill"`, `congress`, `bill_number`, `title`, `policy_area` (string|null), `role` ∈ `sponsor|cosponsor`, `introduced_date`. Folder `data/record/<cid>/`.
- [x] `taxonomy/policy_area_crosswalk.json`: `{version, mappings: [{policy_area, topics: [...]}]}`. Every Congress.gov policy area is listed (unmapped ones → `topics: []`). Validated against `taxonomy/topics.json`.
- [x] `collectors/congress_bills.py` (`name = "congress_bills"`): for candidates with `bioguide_id`, pulls sponsored and cosponsored bills, uses `CONGRESS_API_KEY` (falls back to `DEMO_KEY`). Topics from the crosswalk, `tagged_by: crosswalk@1`.
  - Tests: crosswalk validation (every topic id exists; no duplicate policy areas); fixture mapping; candidate without `bioguide_id` skipped; pagination; retries.
- [x] Add optional `policy_area` to vote schema (D-036). Votes linked to a collected bill by `bill_number` take that bill's topics with `tagged_by: crosswalk@1`.
  - Tests: vote gets topics from its bill; vote with no matching bill keeps `topics: []`.
- [x] Add `congress_bills` to the workflow.

**Acceptance:** crosswalk validates; collector output validates; a known bill's topic mapping is tested.

## Phase 6 — Bio records

- [x] Schema `schemas/bio.schema.json`: `type: "bio"`, `kind` ∈ `office|education|career`, `title`, `organization`, `start_date`, `end_date` (null = current), `location`. Folder `data/bio/<cid>/`. Judgment tier.
- [x] Validator rule: `end_date` ≥ `start_date`.
- [x] Tests: each kind validates; end before start fails; bio path is not in the official tier.
- [x] Seeding is done in Phase 11 (`find-evidence` skill). Here, only a sample record per tracked candidate for Trump and one other.

**Acceptance:** schema and tier tests pass; sample records validate.

## Phase 7 — Outlets, RSS articles, archiving

- [x] `config/outlets.yaml`: the 10 outlets (D-014) with `id`, `name`, `feed_url`, `rater_links` (no rating values, per D-015). Check each feed at build time; drop and log failures in `DECISIONS.md`.
- [x] Schema `schemas/article.schema.json`: `type: "article"`, `outlet_id`, `headline`, `author` (null allowed), `archive_url`, `extraction_status` ∈ `pending|done|skipped`. Folder `data/articles/<cid>/`.
- [x] `matching.py`: a candidate matches an entry if its full name or an alias appears as a whole phrase (case-insensitive). A bare surname never matches (D-009).
  - Tests: full name match; alias match; surname alone → no match; partial token ("Bushel" for "Bush") → no match.
- [x] `archive.py`: anonymous Save Page Now, rate-limited, retries. Failure sets `archive_url: null`.
  - Tests: success; 429 retried; permanent failure → null, record still valid.
- [x] `collectors/rss.py` (`name = "rss"`): reads feeds, dedupes by URL, matches candidates, writes article records with `extraction_status: pending`, no body text stored.
  - Tests: dedupe across runs; feed parse errors do not stop other outlets (per D-023); no full text in any output field.

**Acceptance:** all tests pass with fixture feeds; validator clean; no full article text anywhere in `data/`.

## Phase 8 — Statements, quote and link checks

- [x] Schema `schemas/statement.schema.json`: `type: "statement"`, `quote` (short, max 280 chars), `speaker`, `venue`, `context`, `archive_url`. Folder `data/statements/<cid>/`. Judgment tier.
- [x] Validator rule (D-037): `speaker` must equal the candidate's name or an alias.
- [x] `checks/quotes.py`: fetches the source, checks the quote appears verbatim (whitespace-normalized). Not found → flagged. Fetch failure → warning.
- [x] `checks/links.py`: HEAD/GET reachability. 404 → error. 403, timeout, paywall → warning.
- [x] `python -m tracker.checks --changed` runs both for records changed against `origin/main`.
  - Tests: verbatim match; altered quote flagged; speaker mismatch fails validation; 404 blocks; 403 warns; new-only (unchanged records are not checked).
- [x] Add a CI job running `tracker.checks --changed`.

**Acceptance:** tests pass with `MockTransport`; CI job defined; the job's exit codes are tested.

## Phase 9 — Official positions

- [x] Schema `schemas/position.schema.json`: `type: "position"`, `url`, `capture_date`, `archive_url`, `content_sha256`, `changed` (bool), `key_quotes` (array of ≤5 short strings). Folder `data/positions/<cid>/`. Judgment tier.
- [x] `positions.py`: given a fetched page, computes the hash, compares to the last capture for that URL, sets `changed`, extracts nothing else. Stores no page text.
  - Tests: first capture → `changed: false`; same content → hash equal; altered text → `changed: true`; no full text in the written record.

**Acceptance:** tests pass; no page text stored.

## Phase 10 — Endorsements, appearances, polls

- [x] Schemas: `endorsement` (`endorser`, `endorser_type`, `date`, `source_url`), `appearance` (`event`, `venue`, `host`, `date`, `transcript_url`, `video_url`), `poll` (`pollster`, `value`, `field_start`, `field_end`, `sample`, `population`, `source_url`). Folders under `data/endorsements/`, `data/appearances/`, `data/polls/`, each under `<cid>/`.
- [x] Attribution rule: poll and endorsement records carry the named source, never a project characterization. Validator enforces `pollster` and `endorser` are non-empty.
  - Tests: each schema validates a fixture; missing pollster fails; no stance field accepted.

**Acceptance:** tests pass; validator clean.

## Phase 11 — Disclosures (House Clerk index)

- [x] Schema `schemas/disclosure.schema.json`: `type: "disclosure"`, `filer_name`, `year`, `form`, `filing_date`, `document_url`. Folder `data/disclosures/<cid>/`. Official tier.
- [x] `collectors/house_clerk.py` (`name = "house_clerk"`): reads the annual index for the year and matches filers using `disclosure_names` in the candidate config (exact name list; no fuzzy matching).
  - Tests: fixture index → records; name not in config → skipped; index unchanged → zero writes.
- [x] Add to the workflow.

**Acceptance:** tests pass; validator clean.

## Phase 12 — Media attention and full MCP toolset

- [x] `DataIndex` additions: `media_attention(candidate, outlet, period)` (counts from articles, computed per call), `outside_spending`, `bio`, `disclosures`, `endorsements`, `appearances`, `polls`, `positions`, `bills`.
- [x] `position_timeline(candidate, topic)` covers statements, positions, votes, bills, and executive actions.
- [x] `compare(candidates[], topic)`: side-by-side evidence, no ranking; unknown ids error with the valid list.
- [x] Register all tools in `server.py` per spec §6. Same result shape everywhere (`results`, `count`, `truncated`, `note`).
  - Tests: one per tool; `compare` returns no ordering fields; startup time test (under 5 s with the real data set, else add D-029 SQLite task).

**Acceptance:** all tools registered; tests pass; startup time recorded in `DECISIONS.md`.

## Phase 13 — Claude-assisted skills

- [x] `src/tracker/skillkit.py`: `write_checked(record, root)` validates, refuses stance fields and any record lacking `source_url`, writes via `write_record`.
  - Tests: refuses a stance field; refuses a missing `source_url`; accepts a valid statement.
- [x] Five skills in `.claude/skills/`: `extract-quotes-tags`, `backfill`, `check-positions`, `find-evidence`, `tag-records`. Each takes a candidate id argument, reads its inputs, writes only through `skillkit`, and ends with `tracker.validate` and a PR-ready summary.
- [x] Run each skill once on one candidate as a smoke test. Record the run in `DECISIONS.md`.

**Acceptance:** skillkit tests pass; each skill's smoke run produces validated records; no skill writes outside its folders.

## Phase 14 — CI hardening, docs

- [x] `ci.yml`: add ruff, `tracker.checks --changed`. Pin action versions as they are.
- [x] `collect-official.yml`: run every collector, aggregate failures at the end (D-023). `test_workflows.py` checks the aggregation.
- [x] Docs: `NEUTRALITY.md`, `SOURCES.md` (outlets, pollsters, criteria), `CONTRIBUTING.md`, `README.md` (keys, owner setup status, scope from §4b), `CORRECTIONS.md` (in-place correction, D-013).
- [x] Remove the `README` claim about `data/record/` only; match the layout in spec §6.

**Acceptance:** `scripts/verify.py` exits 0; workflows parse; docs match the spec.

## Phase 15 — Final spec audit

- [x] Walk spec §§2–8 line by line. For each requirement, name the file and test that proves it in `docs/COVERAGE.md`.
- [x] Anything missing is built or logged in `DECISIONS.md` as a known limitation.
- [x] Final `scripts/verify.py` run.

**Acceptance:** `docs/COVERAGE.md` has no empty rows; every gap is either built or in `DECISIONS.md`.

## Known out of scope (logged, not built)

Fact-checks (D-017), OpenStates (D-018), GovInfo (D-031), OpenSecrets (D-012), social posts, 2028 hopefuls (D-005), non-presidential candidacies (D-005), SQLite unless needed (D-029).
