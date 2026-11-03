"""CLI: python -m tracker.collectors <name> [--data DIR]"""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

from tracker.collectors import BUILTIN_MODULES, REGISTRY
from tracker.collectors.base import run_collector
from tracker.validate import REPO_ROOT


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tracker.collectors")
    parser.add_argument("name")
    parser.add_argument("--data", default=str(REPO_ROOT / "data"))
    args = parser.parse_args(argv)

    for module in BUILTIN_MODULES:
        importlib.import_module(module)

    if args.name not in REGISTRY:
        print(f"unknown collector: {args.name}; known: {sorted(REGISTRY)}", file=sys.stderr)
        return 2

    try:
        result = run_collector(REGISTRY[args.name](), Path(args.data))
    except Exception as exc:  # HTTP failures and invalid records both fail the run
        print(f"{args.name} failed: {exc}", file=sys.stderr)
        return 1

    print(f"{args.name}: {result.written} written, {result.unchanged} unchanged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
