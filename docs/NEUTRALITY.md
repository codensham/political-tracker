# Neutrality rules

The project records evidence. It never states what a candidate believes or what their position is. Reviewers enforce these rules on every pull request.

1. **Evidence, not verdicts.** Every record is a dated fact with a source URL: a quote, a vote, a filing, a platform page, a fact-check, a poll, an article. No summaries, sentiment scores, or stance labels authored by the project.
2. **Attribute every judgment.** Fact-check ratings belong to the checker. Poll numbers belong to the pollster. Outlet lean ratings come from a named third-party rater, never from us. Topic tags are the only classifications we add, and each one records how it was tagged.
3. **Candidate's own words only in statements.** Quotes from surrogates, opponents, or officials may appear on article records. They are never returned as the candidate's evidence.
4. **Fixed vocabulary.** Topics come only from `taxonomy/topics.json`. Changing the list needs a pull request with a stated reason.
5. **Same rules for everyone.** Collectors run the same way for every candidate and every outlet in the config. Do not add a candidate or outlet for a reason that is not recorded in `docs/SOURCES.md` or the `inclusion_reason` field.
6. **No copyrighted full text.** Store metadata, the outlet's own headline, and short verbatim quotes. Link to the original and to an archived copy. Government records may be stored in fuller form.
7. **Verbatim quotes.** Every quote must appear word for word in the linked source. Reviewers spot-check quotes against the source before merging.
8. **Corrections are visible.** A correction keeps the prior value in the pull request description. History stays in git.
