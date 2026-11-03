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

## Development

```bash
python -m pytest
python -m tracker.validate data
```
