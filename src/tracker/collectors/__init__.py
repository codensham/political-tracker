"""Collectors. Each collector module registers itself in REGISTRY."""

from __future__ import annotations

from typing import Callable

# Name -> factory. Filled by the collector modules listed in BUILTIN_MODULES.
REGISTRY: dict[str, Callable[[], object]] = {}

# Modules imported by the CLI so their REGISTRY entries exist.
# Later tasks append their module here (e.g. "tracker.collectors.fec").
BUILTIN_MODULES: tuple[str, ...] = ("tracker.collectors.fec", "tracker.collectors.voteview")
