# Contributing

## Set up

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m tracker.validate data
```

`python scripts/verify.py` runs all of the above in one command. Run it before you open a pull request.

Tests come first. Mock HTTP with `httpx.MockTransport`. No test may hit the network.

## Add a record by hand

1. Write the record as JSON in the folder its type uses, for example `data/statements/<candidate-id>/<record-id>.json`. `record_path` in `src/tracker/records.py` is the canonical layout.
2. Set `"collector": "manual"`. Fill in `source_url`, `published_at`, `collected_at`, `candidate_ids` and `topics`.
3. Run `python -m tracker.validate data`. It must exit 0.
4. Open a pull request.

Judgment-bearing records (articles, statements, endorsements, appearances, polls, positions, bios and tags) need the owner's approval. Records under `data/finance/`, `data/record/`, `data/disclosures/` and `data/executive-actions/` are the official tier and may merge automatically once CI passes.

## Rules

Read [NEUTRALITY.md](NEUTRALITY.md) first. A pull request that adds characterization, sentiment, stance labels, verdicts, copyrighted full text, or quotes that do not appear verbatim in the linked source will be closed.

Do not commit `.env`, `.cache/`, or anything under `.superpowers/`. Keys belong in `.env` at the repo root. See the README.

## Add a candidate

Add an entry to `config/candidates.yaml` with `candidacies`, `inclusion_reason` and `as_of`, following [SOURCES.md](SOURCES.md). Then run:

```bash
python -m tracker.candidates
```

Retired fields `status` and `party` are rejected.

## Add an outlet

Add an entry to `config/outlets.yaml` with `id`, `name` and `feed_url`. Check the feed works. If a feed fails, drop the outlet and log the reason in `DECISIONS.md`. Do not add rating values to `rater_links`; only verified links.

## Changing a shared vocabulary

Changes to `taxonomy/topics.json` or `taxonomy/policy_area_crosswalk.json` go through a pull request with a stated reason, as [NEUTRALITY.md](NEUTRALITY.md) requires.

## Decisions

Anything the spec does not settle is logged in `DECISIONS.md` in the same pull request.
