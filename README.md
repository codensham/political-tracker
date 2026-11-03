# Political Tracker

Open, sourced reference data on US presidential candidates (2028 cycle). The project records evidence, with a source and date on every item. It never states a candidate's position in its own words.

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

Tools: `list_candidates`, `get_candidate`, `search_evidence`, `position_timeline`, `get_finance`. Every result includes `source_url` for each record.

## What is in the data

| Folder | Contents | Review |
|---|---|---|
| `data/candidates/` | One file per tracked candidate | Owner |
| `data/finance/` | FEC totals per candidate and cycle | Automatic after CI |
| `data/record/` | Roll-call votes, full career (Voteview) | Automatic after CI |
| `data/disclosures/` | Financial disclosure filings (planned) | Automatic after CI |

Judgment-bearing records (articles, quotes, topic tags, endorsements, positions) need owner approval. See [docs/NEUTRALITY.md](docs/NEUTRALITY.md) and [docs/SOURCES.md](docs/SOURCES.md).

Collection runs daily in GitHub Actions (`.github/workflows/collect-official.yml`) and opens one pull request per run.

## Owner setup (once, after pushing to GitHub)

1. Make the repo public. Settings → General → enable **Allow auto-merge**.
2. Settings → Secrets and variables → Actions:
   - `FEC_API_KEY`: a free key from https://api.data.gov/signup/
   - `BOT_TOKEN`: a fine-grained personal access token with contents and pull-requests write access to this repo. Needed so the bot's pull requests trigger CI.
3. Create the label `official-record`.
4. Settings → Branches → protect `main`: require the `test` status check. Leave required approvals at 0 so official-record PRs can auto-merge; judgment PRs are still reviewed by you before merge.

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m tracker.validate data
python -m tracker.candidates
python -m tracker.collectors voteview
```

Contributor guide: [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md). Corrections: [docs/CORRECTIONS.md](docs/CORRECTIONS.md).

## License

Code: MIT ([LICENSE](LICENSE)). Data: CC BY 4.0 ([DATA_LICENSE](DATA_LICENSE)).
