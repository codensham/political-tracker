# Spec coverage

Each requirement in the [design spec](superpowers/specs/2026-11-03-political-tracker-design.md) is listed with the file that implements it and the test that proves it. Status is one of:

- **Built**: implemented and tested.
- **Partial**: implemented, but the data or a sub-part is not yet complete. The decision that explains it is named.
- **Gap**: not built. The decision that records the gap is named.

Decisions are in [DECISIONS.md](../DECISIONS.md). "Inspection" means the requirement is met by a document or configuration, not by code under test.

## §2 Goals

| Requirement | Implemented in | Proven by | Status |
|---|---|---|---|
| Track every major-party presidential nominee 2000 to 2024 | config/candidates.yaml (10 nominees) | tests/test_nominees_config.py (test_config_has_exactly_the_scoped_nominees, test_candidacies_match_scope) | Built |
| Every record has a source URL and dates | schemas/base.schema.json | tests/test_validate.py, tests/test_skillkit.py | Built |
| Collect regularly; humans review judgment records | .github/workflows/collect-official.yml, collect-articles.yml; src/tracker/tier.py | tests/test_workflows.py, tests/test_tier.py | Built |
| Open data; git history as audit trail | one JSON file per record (src/tracker/records.py) | tests/test_records.py | Built |
| MCP server answers with citations | src/tracker/mcp_server/server.py | tests/test_mcp_toolset.py | Built |
| General candidate database; 2028 candidates added through candidacies | schemas/candidate.schema.json (candidacies) | tests/test_candidate_schema.py | Built |

## §3 Non-goals

Non-goals are not built, by design. The collector registry lists only the built collectors (src/tracker/collectors/__init__.py, BUILTIN_MODULES). Inspection.

## §4 Anti-goals

| Requirement | Implemented in | Proven by | Status |
|---|---|---|---|
| No summaries, sentiment or stance fields | schemas (unevaluatedProperties false); src/tracker/skillkit.py FORBIDDEN_FIELDS | tests/test_attribution.py (stance rejected), tests/test_skillkit.py | Built |
| No copyrighted full text | src/tracker/collectors/rss.py stores headline and metadata; statement quotes limited to 280 characters | tests/test_rss.py, tests/test_checks.py | Built |
| Topic tags only from the fixed taxonomy | src/tracker/validate.py (topic check) | tests/test_validate.py | Built |
| No unverifiable records | base schema requires source_url; src/tracker/checks.py link and quote checks | tests/test_checks.py, tests/test_skillkit.py | Built |
| Collectors run identically for every candidate and outlet | src/tracker/collectors/base.py run_collector | tests/test_collector_base.py | Built |

## §4a Constraints

| Requirement | Implemented in | Proven by | Status |
|---|---|---|---|
| Two review tiers (official auto-merge, judgment needs approval) | src/tracker/tier.py; .github/workflows/ci.yml tier job | tests/test_tier.py, tests/test_workflows.py | Built |
| One batched PR per collector run per dataset | .github/workflows/collect-official.yml, collect-articles.yml | tests/test_workflows.py | Built |
| About 10 fixed outlets | config/outlets.yaml (8 kept) | tests/test_rss.py (test_one_outlet_failing_still_writes_the_rest) | Partial: AP and Washington Post dropped (D-054) |
| Corrections update source fields in place | docs/CORRECTIONS.md; no corrections field in schemas | tests/test_validate.py (test_stance_field_rejected: unknown fields fail) | Built |
| Secrets in git-ignored `.env`; never printed | src/tracker/config.py; src/tracker/http.py redact() | tests/test_config.py, tests/test_http.py | Built |
| Historical backfill is gradual, per candidate | .claude/skills/backfill/SKILL.md | Smoke run only (D-059) | Partial (D-062, D-064) |

## §4b Scope

| Requirement | Implemented in | Proven by | Status |
|---|---|---|---|
| Ten nominees with their candidacies and results | config/candidates.yaml | tests/test_nominees_config.py (test_config_has_exactly_the_scoped_nominees, test_candidacies_match_scope) | Built |
| FEC candidate ID on every candidacy | schemas/candidate.schema.json | tests/test_candidate_schema.py | Built |
| `inclusion_reason` and `as_of` on every entry | schemas/candidate.schema.json (required) | tests/test_candidate_schema.py | Built |
| Trump 2024 principal committee linked | config/candidates.yaml (candidate-level IDs) | Inspection | Partial: only the Republican Nominee Fund committee (D-038) |

## §5 Data in scope

| Dataset | Implemented in | Proven by | Status |
|---|---|---|---|
| Candidates: name, aliases, social accounts, IDs, official site | schemas/candidate.schema.json; src/tracker/candidates.py | tests/test_candidate_schema.py, tests/test_candidates.py | Partial: social accounts empty (D-066) |
| Bio: office, education, career with dates | schemas/bio.schema.json; src/tracker/validate.py (date order) | tests/test_bio.py | Partial: samples only (D-062) |
| Articles: outlet, headline, author, dates, URL, archive, extraction status | schemas/article.schema.json; src/tracker/collectors/rss.py | tests/test_rss.py | Partial: archive links null (D-055) |
| Statements: verbatim quote, speaker is the candidate, date, venue, archive | schemas/statement.schema.json; src/tracker/validate.py speaker_errors | tests/test_checks.py (test_speaker_must_be_candidate_name_or_alias, quote tests) | Partial: 2 Trump statements (D-062) |
| Official positions: hash, change flag, key quotes, no page text | src/tracker/positions.py; schemas/position.schema.json | tests/test_positions.py | Partial: no captures yet (D-067) |
| Track record: votes | src/tracker/collectors/voteview.py; schemas/vote.schema.json | tests/test_voteview.py | Built |
| Track record: bills sponsored and cosponsored | src/tracker/collectors/congress_bills.py; schemas/bill.schema.json | tests/test_congress_bills.py | Built |
| Track record: executive actions | src/tracker/collectors/federal_register.py; schemas/executive_action.schema.json | tests/test_federal_register.py | Built |
| Campaign finance totals per cycle | src/tracker/collectors/fec.py; schemas/finance.schema.json | tests/test_fec.py | Partial: principal committee for Trump (D-038) |
| Outside spending per candidate per cycle | src/tracker/collectors/fec_outside_spending.py; schemas/outside_spending.schema.json | tests/test_fec_outside_spending.py | Built |
| Personal finances: House Clerk filing metadata | src/tracker/collectors/house_clerk.py; schemas/disclosure.schema.json | tests/test_house_clerk.py | Partial: no current matches for nominees (D-057) |
| Personal finances: OGE 278e and Senate eFD | Not built | Not built | Gap (D-063) |
| Endorsements: endorser, date, source | schemas/endorsement.schema.json; find-evidence skill | tests/test_attribution.py | Partial: 1 Trump record (D-062) |
| Polling: value, pollster, field dates, sample, source | schemas/poll.schema.json; find-evidence skill | tests/test_attribution.py | Partial: no poll records (D-062) |
| Media attention computed on each call | src/tracker/mcp_server/index.py media_attention | tests/test_mcp_toolset.py | Built |
| Appearances: event, venue, host, date, transcript or video | schemas/appearance.schema.json; find-evidence skill | tests/test_attribution.py | Partial: no appearance records (D-062) |
| Position timeline query over quotes, positions, votes, bills | src/tracker/mcp_server/index.py position_timeline | tests/test_mcp_toolset.py | Built |
| Outlet lean ratings: link and check date only | config/outlets.yaml (rater_links) | Inspection | Partial: links not filled, no check dates (D-015, D-068) |
| Store metadata, headline and short quotes only | rss.py; statement schema (280 characters) | tests/test_rss.py (test_no_article_text_is_stored), tests/test_checks.py | Built |
| Transient page text not committed | src/tracker/checks.py (fetch only, nothing written); cache outside data/ | tests/test_index_cache.py (cache location) | Built |
| Archive link at collection time | src/tracker/archive.py | tests/test_rss.py (test_archive_url_recorded_when_saved, test_archive_failure_leaves_null_and_record_valid) | Partial: Wayback unreachable (D-055) |
| Government records may be stored in fuller form | schemas store the official fields | Inspection | Built |
| Every quote verbatim in its source; CI checks it | src/tracker/checks.py | tests/test_checks.py | Built |
| Statements hold only the candidate's own words | src/tracker/validate.py speaker_errors | tests/test_checks.py (test_speaker_must_be_candidate_name_or_alias) | Built |
| Collectors send the project User-Agent, no email | src/tracker/http.py USER_AGENT | tests/test_http.py | Built |
| Topic tags record how they were tagged (`tagged_by`) | schemas/base.schema.json (tagged_by); src/tracker/tagging.py | tests/test_tagging.py | Built |
| Policy-area crosswalk, versioned, changes by PR | taxonomy/policy_area_crosswalk.json; src/tracker/crosswalk.py | tests/test_tagging.py | Built |
| Executive-action tagging through the skill, reviewed | .claude/skills/tag-records/SKILL.md | Smoke run: articles and statements only (D-059) | Partial (D-059) |
| Fixed topic taxonomy, changes by PR | taxonomy/topics.json | tests/test_validate.py | Built |

## §6 Architecture

| Requirement | Implemented in | Proven by | Status |
|---|---|---|---|
| Python 3.12, JSON records validated by JSON Schema draft 2020-12 | src/tracker/validate.py | tests/test_validate.py | Built |
| FastMCP server over stdio | src/tracker/mcp_server/server.py, __main__.py | tests/test_mcp_server.py | Built |
| ruff in CI | .github/workflows/ci.yml (test job) | tests/test_workflows.py | Built |
| Deterministic collectors run on a schedule | .github/workflows/collect-official.yml (daily), collect-articles.yml (daily) | tests/test_workflows.py | Built |
| Five Claude-assisted skills, each taking a candidate ID | .claude/skills/ (five SKILL.md files) | Smoke runs (D-059); check-positions and backfill not run (D-067) | Partial (D-067) |
| Skill writes only through a tested helper that refuses stance fields | src/tracker/skillkit.py write_checked | tests/test_skillkit.py | Built |
| CI on every PR: tests, schema, taxonomy, duplicates, ruff | .github/workflows/ci.yml; src/tracker/validate.py duplicate_keys | tests/test_duplicates.py, tests/test_workflows.py | Built |
| Link reachability and quote verification on changed records | src/tracker/checks.py; ci.yml checks job | tests/test_checks.py | Built |
| Official auto-merge on green CI; judgment PRs need approval | ci.yml tier job; src/tracker/tier.py | tests/test_tier.py, tests/test_workflows.py | Built |
| Every collector runs even if one fails; workflow fails at the end | collect-official.yml, collect-articles.yml | tests/test_workflows.py | Built |
| Collector schedules: official daily, RSS daily on collect/articles | collect-official.yml, collect-articles.yml | tests/test_workflows.py | Built |
| MCP tools: list_candidates, get_candidate, search_evidence, position_timeline, get_finance | src/tracker/mcp_server/server.py | tests/test_mcp_toolset.py, tests/test_mcp_server.py | Built |
| MCP tools: get_outside_spending, get_bio, get_disclosures, get_endorsements, get_appearances, get_polls | src/tracker/mcp_server/server.py | tests/test_mcp_toolset.py | Built |
| MCP tools: media_attention, compare | src/tracker/mcp_server/server.py; index.py | tests/test_mcp_toolset.py | Built |
| Result shape: results, count, truncated, note; source_url on each record | src/tracker/mcp_server/server.py _ok | tests/test_mcp_toolset.py (common shape) | Built |
| Unknown candidate IDs return an error that lists valid IDs | src/tracker/mcp_server/index.py UnknownCandidate | tests/test_mcp_toolset.py (compare unknown id) | Built |
| compare returns no ranking or ordering fields | src/tracker/mcp_server/index.py compare | tests/test_mcp_toolset.py (no ordering fields) | Built |
| Startup under 5 s; SQLite cache built from JSON when needed | src/tracker/mcp_server/cache.py | tests/test_index_cache.py | Built (cold start 8.3 s, warm 1.15 s; D-058) |
| Repository layout as in §6 | src/tracker/records.py TYPE_DIRS, record_path | tests/test_records.py | Built |
| Candidate record v2 fields (name, aliases, socials, candidacies, IDs, inclusion_reason) | schemas/candidate.schema.json | tests/test_candidate_schema.py | Built |
| list_candidates filters by office, year, result | src/tracker/mcp_server/index.py candidates | tests/test_mcp_index.py | Built |

## §7 Build order and MVP criterion

| Requirement | Implemented in | Proven by | Status |
|---|---|---|---|
| Build order items 1 to 12 | BUILD_PLAN.md phases 0 to 14 | verify.py (suite) | Built |
| Every dataset has a schema, a collector or skill, tests and an MCP tool | §5 rows above | Rows above | Built |
| At least one real record per tracked candidate where data exists | Sample data only | Not met for most candidates | Gap (D-062) |

## §8 Licensing and governance

| Requirement | Implemented in | Proven by | Status |
|---|---|---|---|
| Code under MIT | LICENSE | Inspection | Built |
| Data under CC BY 4.0 | DATA_LICENSE; README.md | Inspection | Built |
| docs/NEUTRALITY.md states the rules in §4 and §5 | docs/NEUTRALITY.md | Inspection | Built |
| Respect source terms and robots.txt; prefer APIs and RSS | docs/CONTRIBUTING.md; collectors use APIs and RSS | Inspection; no robots.txt check in code | Gap (D-065) |
