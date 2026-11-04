"""CLI: python -m tracker.mcp_server [--data DIR]  (serves MCP over stdio)"""

from __future__ import annotations

import argparse
from pathlib import Path

from tracker.mcp_server.server import configure, mcp
from tracker.validate import REPO_ROOT


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="tracker.mcp_server")
    parser.add_argument("--data", default=str(REPO_ROOT / "data"))
    args = parser.parse_args(argv)
    configure(Path(args.data))
    mcp.run()


if __name__ == "__main__":
    main()
