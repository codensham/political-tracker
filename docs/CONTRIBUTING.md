# Contributing

## Set up

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m tracker.validate data
```

## Add a record by hand

1. Write the record as JSON in the right folder (for example `data/record/<candidate-id>/<record-id>.json`). The folder is set by `record_path` in `src/tracker/records.py`.
2. Set `"collector": "manual"` and fill in `source_url`, `published_at`, `collected_at`, `candidate_ids`, and `topics`.
3. Run `python -m tracker.validate data`. It must exit 0.
4. Open a pull request. Judgment records (articles, quotes, tags, endorsements) need the owner's approval. Records in `data/finance/`, `data/record/`, or `data/disclosures/` are official-record PRs and may merge automatically once CI passes.

## Rules

Read [NEUTRALITY.md](NEUTRALITY.md) first. A pull request that adds characterization, sentiment, stance labels, or copyrighted full text will be closed.

## Adding a candidate

Add an entry to `config/candidates.yaml` with `inclusion_reason` and `as_of`, following the criteria in [SOURCES.md](SOURCES.md). Then run `python -m tracker.candidates`.
