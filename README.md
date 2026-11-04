# Political Tracker

Open, sourced reference data on US presidential candidates. Covers the major-party presidential nominees from 2000 to 2024, with their full political career, and any 2028 contender added under the same rule. The project records evidence, with a source and a date on every item. It never states a candidate's position in its own words. The full design is in [the spec](docs/superpowers/specs/2026-11-03-political-tracker-design.md).

## Use it from an AI assistant (MCP)

Install from a clone of this repo:

```bash
python -m pip install -e .
```

Add this to your MCP client config (Claude Desktop or Claude Code), replacing the path with your clone:

```json
{
  "mcpServers": {
    "political-tracker": {
      "command": "python",
      "args": ["-m", "tracker.mcp_server", "--data", "C:/path/to/Political Tracker/data"]
    }
  }
}
```

The server loads the data at startup and keeps a SQLite cache in `.cache/`. The first start after a data change rebuilds the cache, which takes several seconds. Later starts take about a second.

Tools:

| Tool | What it returns |
|---|---|
| `list_candidates` | Candidates with a candidacy matching `office`, `year` or `result` |
| `get_candidate` | Name, aliases, candidacies and IDs |
| `search_evidence` | Statements, positions, votes, bills, executive actions, articles, endorsements, appearances and polls |
| `position_timeline` | Statements, positions, votes, bills and executive actions on one topic, oldest first |
| `compare` | Evidence on one topic for several candidates, in the order given. Nothing is ranked |
| `get_finance` | FEC totals per cycle |
| `get_outside_spending` | Independent expenditures per committee per cycle |
| `get_bio` | Offices, education and career entries |
| `get_disclosures` | House financial disclosure filings |
| `get_endorsements` | Endorsements, attributed to the endorser |
| `get_appearances` | Public appearances |
| `get_polls` | Polls, attributed to the pollster |
| `media_attention` | Article counts per candidate and outlet, computed on each call |

Every result has `results`, `count`, `truncated` and `note`. Every record in it has `source_url`. An unknown candidate ID returns an error that lists the valid IDs.

## What is in the data

| Folder | Contents | Review |
|---|---|---|
| `data/candidates/` | One file per tracked candidate | Owner |
| `data/finance/` | FEC totals and outside spending per candidate and cycle | Automatic after CI |
| `data/record/` | Roll-call votes and bills sponsored or cosponsored | Automatic after CI |
| `data/executive-actions/` | Executive orders, proclamations and memoranda | Automatic after CI |
| `data/disclosures/` | House financial disclosure filing metadata | Automatic after CI |
| `data/bio/` | Offices, education and career entries | Owner |
| `data/articles/` | Outlet headlines and metadata, one per article | Owner |
| `data/statements/` | Verbatim quotes from the candidate's own words | Owner |
| `data/positions/` | Official platform snapshots: hash, change flag, key quotes | Owner |
| `data/endorsements/`, `data/appearances/`, `data/polls/` | Attributed evidence from primary sources | Owner |

The folder layout is in spec §6. Judgment-bearing records need owner approval. See [NEUTRALITY](docs/NEUTRALITY.md) and [SOURCES](docs/SOURCES.md).

## Collection

Two scheduled workflows open pull requests:

- `.github/workflows/collect-official.yml` runs every official collector daily. Its pull request auto-merges once CI passes. A collector that fails does not stop the others; the workflow fails at the end.
- `.github/workflows/collect-articles.yml` collects outlet feeds daily into one pull request on `collect/articles`, which needs owner review.

Claude-assisted skills in `.claude/skills/` run on demand, in a Claude Code session.

## Owner setup (once, after pushing to GitHub)

1. Make the repo public. Settings → General → enable **Allow auto-merge**.
2. Settings → Secrets and variables → Actions:
   - `FEC_API_KEY`: a free key from https://api.data.gov/signup/. Without it the collectors use `DEMO_KEY`, which is rate-limited.
   - `BOT_TOKEN`: a fine-grained personal access token with contents and pull-requests write access to this repo. Needed so the bot's pull requests trigger CI.
3. Create the label `official-record`.
4. Settings → Branches → protect `main`: require the `test` status check. Leave required approvals at 0 so official-record PRs can auto-merge; judgment PRs are still reviewed before merge.

Local keys go in a `.env` file at the repo root, which git ignores. Variables are `FEC_API_KEY`, `CONGRESS_API_KEY` and `GOVINFO_API_KEY`; a blank value counts as unset. A git worktree does not contain `.env`, so copy it into the worktree root.

### Owner setup status

Not yet done: the repo is not pushed to GitHub, so the secrets, label and branch protection above are not set. The archive decision (D-055) and the Trump 2024 committee check (D-038) are open. The FEC key used during development should be rotated (D-041).

## Development

```bash
python -m pip install -e ".[dev]"
python scripts/verify.py
```

`verify.py` runs ruff, the tests and record validation. Contributor guide: [CONTRIBUTING](docs/CONTRIBUTING.md). Corrections: [CORRECTIONS](docs/CORRECTIONS.md). Known gaps and decisions: [DECISIONS.md](DECISIONS.md) and [COVERAGE.md](docs/COVERAGE.md).

## License

Code: MIT ([LICENSE](LICENSE)). Data: CC BY 4.0 ([DATA_LICENSE](DATA_LICENSE)). Third-party content such as quotes and headlines remains its owners'; the project relies on short attributed excerpts.
