# Foundation & Official Records Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A working repo where official-record collectors (FEC finance, Voteview career votes) write schema-valid JSON records, CI validates every PR, official-record PRs auto-merge, and a local MCP server answers candidate questions with citations.

**Architecture:** A `tracker` Python package holds record I/O, schema validation, collectors and the MCP server. Data lives as one JSON file per record under `data/`, validated by JSON Schemas in `schemas/`. Deterministic collectors run in GitHub Actions and open batched PRs; a path-based tier check decides whether a PR may auto-merge.

**Tech Stack:** Python 3.12, `jsonschema`, `httpx`, `pyyaml`, `mcp` (official Python SDK, FastMCP), `pytest`. GitHub Actions + `peter-evans/create-pull-request`.

**Spec:** `docs/superpowers/specs/2026-11-03-political-tracker-design.md`

**Follow-up plans (not in this plan):** 2 — outlets, RSS articles, Wayback archiving, CI quote check. 3 — Claude-assisted skills (quote/tag extraction, historical backfill via GDELT/Wayback CDX). 4 — Congress.gov bills + policy areas, official positions, disclosures, endorsements, bio. 5 — fact-checks, polls, appearances, media attention.

## Global Constraints

- Zero budget: no paid APIs or services. FEC uses `FEC_API_KEY` env var, falling back to `DEMO_KEY`.
- One JSON file per record. Written UTF-8, `indent=2`, `sort_keys=True`, trailing `\n`, LF line endings (`.gitattributes`: `*.json text eol=lf`).
- Every record has: `id`, `type`, `candidate_ids`, `source_url`, `published_at`, `collected_at`, `collector`, `topics`. Optional: `archive_url`, `tagged_by`.
- `topics` values must exist in `taxonomy/topics.json`. Official records may have `topics: []`.
- No full copyrighted text in any record. Government data may be stored in full.
- The project never characterizes a position: no summary, sentiment, or stance fields in any schema; MCP output is records + citations only.
- Record IDs match `^[a-z0-9][a-z0-9-]*$` (filesystem-safe on Windows).
- Official-record tier = only paths under `data/finance/`, `data/record/`, `data/disclosures/`. Anything else needs human review.

## Review Focus

1. **Rerunning a collector with unchanged source data** → zero file changes (`collected_at` is not rewritten when content is otherwise identical). Test in Task 4.
2. **Candidate with no congressional career** (no `icpsr`) → Voteview collector yields nothing for them, no error. Test in Task 6.
3. **Candidate who served in both House and Senate** → votes from both chambers collected. Test in Task 6.
4. **FEC returns 429 / 5xx** → retried with backoff up to 3 times, then the run fails with a non-zero exit; already-written records stay valid. Test in Task 5.
5. **MCP tool called with an unknown candidate id** → error message listing valid ids, no crash. Test in Task 7.

---

### Task 1: Scaffold, common schema, record I/O

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `.gitattributes`, `src/tracker/__init__.py`, `src/tracker/records.py`, `schemas/base.schema.json`
- Test: `tests/test_records.py`

**Interfaces:**
- Produces:
  - `TYPE_DIRS: dict[str, str]` = `{"candidate": "candidates", "finance": "finance", "vote": "record"}`
  - `record_path(record: dict, root: Path) -> Path` — `candidate` → `root/candidates/<id>.json`; others → `root/<dir>/<candidate_ids[0]>/<id>.json`
  - `write_record(record: dict, root: Path) -> bool` — returns `True` if file created/changed, `False` if identical content (ignoring `collected_at`) already exists
  - `load_records(root: Path, type: str | None = None) -> Iterator[dict]`
  - `now_iso() -> str` (UTC, `YYYY-MM-DDTHH:MM:SSZ`)

- [ ] **Step 1:** `pyproject.toml` with src layout, deps above, `[project.optional-dependencies] dev = ["pytest"]`, pytest `testpaths = ["tests"]`. Install: `python -m pip install -e .[dev]`.
- [ ] **Step 2: Write failing tests** in `tests/test_records.py`:
  - `test_candidate_path`: `record_path({"id":"jane-doe","type":"candidate",...}, tmp)` == `tmp/"candidates"/"jane-doe.json"`
  - `test_vote_path`: type `vote`, `candidate_ids=["jane-doe"]`, id `vote-s117-42-jane-doe` → `tmp/"record"/"jane-doe"/"vote-s117-42-jane-doe.json"`
  - `test_roundtrip`: write then `list(load_records(tmp, "vote"))` == `[record]`
  - `test_rewrite_ignores_collected_at`: second write with only `collected_at` changed returns `False` and file bytes unchanged
  - `test_rewrite_detects_change`: changing any other field returns `True`
  - `test_format`: file ends with `"\n"`, contains no `"\r"`, keys sorted
- [ ] **Step 3:** Run `python -m pytest tests/test_records.py -v` → FAIL (module missing).
- [ ] **Step 4:** Implement `records.py`. Write with `newline="\n"`.
- [ ] **Step 5:** Write `schemas/base.schema.json` (draft 2020-12): required common fields from Global Constraints; `id` pattern; `candidate_ids` array of id-pattern strings, minItems 1 (for `candidate`, contains its own id); `source_url` `format: uri`; `topics` array of strings; `collector` string matching `^([a-z0-9_]+@\d+\.\d+|manual)$`; `additionalProperties` allowed (type schemas restrict).
- [ ] **Step 6:** Run tests → PASS. Commit `feat: record I/O and base schema`.

### Task 2: Type schemas, taxonomy, validator CLI

**Files:**
- Create: `schemas/candidate.schema.json`, `schemas/finance.schema.json`, `schemas/vote.schema.json`, `taxonomy/topics.json`, `src/tracker/validate.py`
- Test: `tests/test_validate.py`

**Interfaces:**
- Consumes: `load_records`, `record_path` (Task 1)
- Produces:
  - `validate_record(record: dict) -> list[str]` — empty list = valid
  - `validate_tree(root: Path) -> dict[Path, list[str]]` — only invalid files; also flags a file whose location ≠ `record_path(record)`
  - CLI `python -m tracker.validate <data_dir>` — prints errors, exit 1 if any

Schemas (each `allOf` base + type fields; `additionalProperties: false` over the union of base + type fields):
- **candidate:** `name`, `party`, `status` ∈ `potential|declared|withdrawn|nominee`, `fec_candidate_ids` (array), `icpsr` (int|null), `bioguide_id` (str|null), `official_site` (uri|null), `inclusion_reason` (str).
- **finance:** `cycle` (int), `receipts`, `disbursements`, `cash_on_hand_end`, `debts_owed` (numbers), `coverage_start`, `coverage_end` (dates), `fec_candidate_id`.
- **vote:** `chamber` ∈ `house|senate`, `congress` (int), `rollnumber` (int), `vote_date` (date), `question` (str|null), `bill_number` (str|null), `vote_result` (str|null), `cast` ∈ `yea|nay|present|not_voting`.

`taxonomy/topics.json`: `{"version": 1, "topics": [{"id": "...", "label": "..."}]}` with ids: `economy, taxes, healthcare, immigration, foreign-policy, defense, climate-energy, environment, guns, abortion, criminal-justice, education, civil-rights, labor, trade, technology, elections-democracy, government-ethics, housing, agriculture`.

- [ ] **Step 1: Write failing tests:**
  - `test_valid_vote_passes` (full valid fixture) → `[]`
  - `test_missing_source_url_fails` → errors mention `source_url`
  - `test_unknown_topic_fails`: `topics=["not-a-topic"]` → error mentions `not-a-topic`
  - `test_stance_field_rejected`: candidate with extra `stance` key → error
  - `test_bad_status_fails`: `status="frontrunner"` → error
  - `test_bad_id_fails`: id `Jane Doe` → error
  - `test_misplaced_file_flagged`: valid vote written to wrong dir → `validate_tree` reports it
  - `test_cli_exit_codes`: `subprocess` run on clean tmp dir → 0; with an invalid file → 1
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement with `jsonschema.Draft202012Validator` + `FormatChecker`; topic check in Python against taxonomy.
- [ ] **Step 4:** Run → PASS. Commit `feat: schemas, taxonomy, validator`.

### Task 3: Candidate config and sync

**Files:**
- Create: `config/candidates.yaml`, `src/tracker/candidates.py`, `docs/SOURCES.md`
- Test: `tests/test_candidates.py`

**Interfaces:**
- Consumes: `write_record`, `validate_record`
- Produces:
  - `load_config(path: Path) -> list[dict]` — candidate entries
  - `sync_candidates(config_path: Path, root: Path) -> int` — writes candidate records, returns count changed; `collector="candidates@1.0"`, `source_url` = `official_site` or FEC candidate page `https://www.fec.gov/data/candidate/<first fec id>/`
  - CLI `python -m tracker.candidates`

Config entry fields mirror the candidate schema minus common fields. `docs/SOURCES.md` documents inclusion criteria (my call, from spec §9): include if the person (a) filed FEC Form 2 for the 2028 presidential race, or (b) is not yet filed but appears in ≥2 named national primary polls at ≥2%. `inclusion_reason` records which, with source. The implementer seeds the config from FEC's 2028 presidential filer list (`/v1/candidates/?office=P&election_year=2028`) and current polling, applying the criteria, and lists the sources used in `SOURCES.md`.

- [ ] **Step 1: Failing tests:** `test_sync_writes_valid_records` (2-entry fixture YAML → 2 files, both validate); `test_sync_idempotent` (second run returns 0); `test_duplicate_id_rejected` (raises `ValueError`).
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run → PASS.
- [ ] **Step 5:** Seed `config/candidates.yaml`, run `python -m tracker.candidates`, then `python -m tracker.validate data` → exit 0.
- [ ] **Step 6:** Commit `feat: candidate config and sync`.

### Task 4: Collector base and runner

**Files:**
- Create: `src/tracker/collectors/__init__.py`, `src/tracker/collectors/base.py`, `src/tracker/http.py`
- Test: `tests/test_collector_base.py`, `tests/test_http.py`

**Interfaces:**
- Produces:
  - `class Collector(Protocol)`: `name: str`, `version: str`, `collect(candidates: list[dict]) -> Iterable[dict]`
  - `run_collector(c: Collector, root: Path) -> RunResult` — loads candidate records from `root`, stamps `collector=f"{name}@{version}"` and `collected_at`, validates each record (invalid → raise `InvalidRecord` with errors, nothing written for that record), writes via `write_record`
  - `@dataclass RunResult: written: int; unchanged: int`
  - `get_json(client: httpx.Client, url: str, params: dict | None = None) -> dict` — retries on 429/5xx up to 3 times with exponential backoff (base 1s; injectable `sleep` for tests), raises `httpx.HTTPStatusError` after
  - `get_bytes(client, url) -> bytes` — same retry policy
- CLI `python -m tracker.collectors <name> [--data data]` dispatching via a `REGISTRY: dict[str, Callable[[], Collector]]`.

- [ ] **Step 1: Failing tests:** `test_run_writes_and_counts` (fake collector, 2 records → `RunResult(2,0)`); `test_rerun_unchanged` (Review Focus 1: second run → `RunResult(0,2)`, `git`-style byte equality of files); `test_invalid_record_raises`; `test_retry_then_success` (MockTransport 429, 200 → returns JSON, sleep called once); `test_retry_exhausted` (four 503s → raises).
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run → PASS. Commit `feat: collector base, runner, http retry`.

### Task 5: FEC finance collector

**Files:**
- Create: `src/tracker/collectors/fec.py`, `tests/fixtures/fec_totals.json`
- Test: `tests/test_fec.py`

**Interfaces:**
- Consumes: `Collector`, `get_json`, `REGISTRY`
- Produces: `class FecFinanceCollector` (`name="fec_finance"`, `version="1.0"`), registered as `fec_finance`. Constructor takes optional `httpx.Client`.

Behavior: for each candidate and each `fec_candidate_ids` entry, GET `https://api.open.fec.gov/v1/candidate/{id}/totals/` with `api_key` (env `FEC_API_KEY` or `DEMO_KEY`), `per_page=100`. One record per result row: id `finance-<candidate_id>-<fec_id lowercased>-<cycle>`, field mapping `receipts`, `disbursements`, `last_cash_on_hand_end_period`→`cash_on_hand_end`, `last_debts_owed_by_committee`→`debts_owed`, `coverage_start_date`/`coverage_end_date`→date part, `published_at`=`coverage_end`, `source_url`=`https://www.fec.gov/data/candidate/{id}/?cycle={cycle}`, `topics=[]`. Fixture is a trimmed real response saved by the implementer.

- [ ] **Step 1: Failing tests:** `test_maps_fixture` (MockTransport serving fixture → exact field values from fixture); `test_records_validate`; `test_candidate_without_fec_ids_skipped`; `test_429_retried` (Review Focus 4: 429 then fixture → success); `test_cli_nonzero_on_failure` (persistent 500 → `python -m tracker.collectors fec_finance` exits non-zero, earlier written files still validate).
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run → PASS. Commit `feat: FEC finance collector`.

### Task 6: Voteview career votes collector

**Files:**
- Create: `src/tracker/collectors/voteview.py`, `tests/fixtures/voteview/S117_votes.csv`, `S117_rollcalls.csv`, `H115_votes.csv`, `H115_rollcalls.csv`
- Test: `tests/test_voteview.py`

**Interfaces:**
- Consumes: `Collector`, `get_bytes`, `REGISTRY`
- Produces: `class VoteviewCollector` (`name="voteview"`, `version="1.0"`), registered as `voteview`. Constructor takes optional `httpx.Client`, optional `cache_dir: Path` (default `.cache/voteview`, gitignored).

Behavior: skip candidates with `icpsr` null (Review Focus 2). Find the member's congresses/chambers from `https://voteview.com/static/data/out/members/HSall_members.csv` (filter `icpsr`). For each (chamber, congress) download `https://voteview.com/static/data/out/votes/{H|S}{congress:03d}_votes.csv` and `.../rollcalls/{H|S}{congress:03d}_rollcalls.csv` (cache on disk). Join on `rollnumber`. `cast_code` mapping: 1–3→`yea`, 4–6→`nay`, 7–8→`present`, 9→`not_voting`, 0→skip. Record id `vote-<h|s><congress>-<rollnumber>-<candidate_id>`; `vote_date`/`published_at` from rollcall `date`; `question`=`vote_question`, `bill_number`, `vote_result`; `source_url`=`https://voteview.com/rollcall/R{H|S}{congress:03d}{rollnumber:04d}`; `topics=[]`. Fixtures: a few rows from real files, plus a members fixture.

- [ ] **Step 1: Failing tests:** `test_cast_mapping` (each code 0–9); `test_join_and_fields` (fixture → exact record for one known roll call); `test_no_icpsr_skipped`; `test_both_chambers` (Review Focus 3: member rows in H115 and S117 → records from both); `test_downloads_cached` (second collect makes no HTTP calls).
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement with `csv.DictReader`. **Step 4:** Run → PASS. Commit `feat: Voteview career votes collector`.

### Task 7: MCP server

**Files:**
- Create: `src/tracker/mcp_server/__init__.py`, `index.py`, `server.py`, `__main__.py`
- Test: `tests/test_mcp_index.py`, `tests/test_mcp_server.py`

**Interfaces:**
- Consumes: `load_records`
- Produces:
  - `class DataIndex`: `load(root: Path) -> DataIndex` (classmethod); `candidates(status: str | None) -> list[dict]`; `candidate(cid: str) -> dict` (raises `UnknownCandidate` whose message lists valid ids — Review Focus 5); `evidence(cid, topic=None, date_from=None, date_to=None, types=None) -> list[dict]` sorted by `published_at` ascending; `finance(cid, cycle=None) -> list[dict]`
  - `server.py`: FastMCP app `"political-tracker"` with tools `list_candidates(status?)`, `get_candidate(candidate)`, `search_evidence(candidate, topic?, date_from?, date_to?, types?, limit=50)`, `position_timeline(candidate, topic)` (= `evidence` filtered to topic), `get_finance(candidate, cycle?)`. Each tool returns `{"results": [...records...], "count": n, "note": "Records are sourced evidence; see source_url on each. This server does not characterize positions."}`. Unknown candidate → tool returns `{"error": str(exc)}`.
  - Run: `python -m tracker.mcp_server --data data` (stdio).
- Tool docstrings tell the calling AI to cite `source_url` and not infer stances beyond the records.

- [ ] **Step 1: Failing tests:** `test_evidence_sorted_and_filtered` (fixture tree: votes on 3 dates, filter by date range); `test_topic_filter` (only records whose `topics` contain topic); `test_unknown_candidate_lists_ids`; `test_tools_registered` (the five tool names present on the FastMCP app); `test_tool_result_shape` (call `search_evidence` function directly → has `results`, `count`, `note`, every result has `source_url`).
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run → PASS.
- [ ] **Step 5:** Add `README.md` section showing a Claude Code / Claude Desktop MCP config entry for the stdio server. Commit `feat: MCP server`.

### Task 8: CI, scheduled collection, review tiers, project docs

**Files:**
- Create: `src/tracker/tier.py`, `.github/workflows/ci.yml`, `.github/workflows/collect-official.yml`, `docs/NEUTRALITY.md`, `docs/CONTRIBUTING.md`, `docs/CORRECTIONS.md`, `LICENSE` (MIT), `DATA_LICENSE` (CC BY 4.0), `README.md` (expand)
- Test: `tests/test_tier.py`

**Interfaces:**
- Produces: `classify_paths(paths: list[str]) -> Literal["official", "judgment"]`; CLI `python -m tracker.tier` reads changed paths from stdin, prints the tier.

- **ci.yml** (on `pull_request`, `push` to `main`): Python 3.12, install, `python -m pytest`, `python -m tracker.validate data`, then a `tier` job that computes `git diff --name-only origin/main...HEAD | python -m tracker.tier` and, if `official` and the PR has label `official-record`, runs `gh pr merge --auto --squash`.
- **collect-official.yml** (`schedule: cron "0 9 * * *"` + `workflow_dispatch`): runs `tracker.candidates`, `tracker.collectors fec_finance`, `tracker.collectors voteview`; then `peter-evans/create-pull-request` (pinned version), branch `collect/official`, title `Official records update <date>`, label `official-record`. One PR per run, updated in place. Uses `secrets.FEC_API_KEY`.
- **Docs:** `NEUTRALITY.md` restates spec §4, §5 content rules, and the evidence-not-verdict principle as reviewer rules. `CONTRIBUTING.md`: manual records use `collector: "manual"`, same schemas, same PR path; how to run tests/validator. `CORRECTIONS.md`: open an issue or PR; corrections note the prior value in the PR; history is git.

- [ ] **Step 1: Failing tests:** `test_official_paths` (only `data/finance/...`, `data/record/...`, `data/disclosures/...` → `official`); `test_mixed_is_judgment` (one official + `data/candidates/x.json` → `judgment`); `test_code_change_is_judgment` (`src/...` → `judgment`); `test_empty_is_judgment`.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run → PASS.
- [ ] **Step 5:** Write workflows and docs. Validate workflow YAML parses: `python -c "import yaml,sys;[yaml.safe_load(open(f)) for f in sys.argv[1:]]" .github/workflows/*.yml` → no error.
- [ ] **Step 6:** End-to-end local check: `python -m tracker.candidates && python -m tracker.collectors fec_finance && python -m tracker.collectors voteview && python -m tracker.validate data` → exit 0; rerun collectors → `git status --porcelain data` empty.
- [ ] **Step 7:** Commit `feat: CI, scheduled official collection, review tiers, docs`.

**Owner setup after merge (manual, documented in README):** create public GitHub repo, push, enable "Allow auto-merge", add `FEC_API_KEY` secret (free from api.data.gov), create `official-record` label, add branch protection requiring CI.
