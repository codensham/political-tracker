# Political Tracker — agent guide

## Spec

Single source of truth: `docs/superpowers/specs/2026-11-03-political-tracker-design.md`. Read it fully before changing anything. Foundation plan (historical): `docs/superpowers/plans/2026-11-03-foundation-and-official-records.md`.

## Stack

- Python 3.12 (CI pins 3.12). Package `tracker` in `src/`, layout via setuptools.
- Deps: `jsonschema[format]`, `httpx`, `pyyaml`, `mcp` (FastMCP, <2). Dev: `pytest`, `ruff`.
- Data: JSON files in `data/`, validated by `schemas/*.schema.json` (draft 2020-12).
- CI: GitHub Actions (`.github/workflows/`). Scheduled collection opens PRs.

## Build, test, run

```bash
python -m pip install -e ".[dev]"     # install
python -m pytest                       # tests
python -m ruff check .                 # lint
python -m tracker.validate data        # validate all records (exit 0 = clean)
python scripts/verify.py               # everything above, one command (once built, BUILD_PLAN Phase 0)
python -m tracker.candidates           # sync candidate records from config
python -m tracker.collectors <name>    # fec_finance | voteview | federal_register | ...
python -m tracker.mcp_server --data data   # MCP server over stdio
```

## Secrets

- Keys live in `.env` at the repo root. It is git-ignored. Never print, log or commit key values.
- Variables: `FEC_API_KEY`, `CONGRESS_API_KEY`, `GOVINFO_API_KEY`. Blank means unset.
- Missing `FEC_API_KEY` falls back to `DEMO_KEY` (rate-limited).
- Git worktrees do not contain `.env`. Copy it into the worktree root, or the collectors will use `DEMO_KEY`.

## Conventions

- One JSON file per record. UTF-8, `indent=2`, `sort_keys=True`, trailing newline, LF line endings.
- Record IDs match `^[a-z0-9][a-z0-9-]*$`.
- Every record has `id, type, candidate_ids, source_url, published_at, collected_at, collector, topics`.
- `topics` values must exist in `taxonomy/topics.json`.
- Never add stance, sentiment, summary or verdict fields. Never store full copyrighted text.
- Collectors run identically for every candidate and outlet in the config.
- Records under `data/finance/`, `data/record/`, `data/disclosures/`, `data/executive-actions/` are the official tier. Everything else needs review.
- Tests come first (TDD). Mock HTTP with `httpx.MockTransport`. No test hits the network.
- Never skip, delete or weaken a test to make it pass. Fix the cause.
- Commit messages: imperative, short subject, no attribution lines.

## Progress and decisions

- Progress is tracked in `BUILD_PLAN.md`. Check boxes as work completes.
- Commit after each completed phase.
- Log any decision not covered by the spec in `DECISIONS.md`.

## Do not

- Do not push, open PRs, or touch the GitHub repo settings without asking.
- Do not commit `.env`, `.cache/`, or anything under `.superpowers/`.
- Do not run Claude-assisted skills or write judgment-bearing data outside a skill's helper.
