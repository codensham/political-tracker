"""Collectors. Each collector module registers itself in REGISTRY."""

from __future__ import annotations

from collections.abc import Callable

# Name -> factory. Filled by the collector modules listed in BUILTIN_MODULES.
REGISTRY: dict[str, Callable[[], object]] = {}

# Modules imported by the CLI so their REGISTRY entries exist.
# Later tasks append their module here (e.g. "tracker.collectors.fec").
BUILTIN_MODULES: tuple[str, ...] = (
    "tracker.collectors.fec",
    "tracker.collectors.voteview",
    "tracker.collectors.federal_register",
    "tracker.collectors.fec_outside_spending",
    "tracker.collectors.congress_bills",
)
