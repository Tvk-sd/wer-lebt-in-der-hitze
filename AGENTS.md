# Tree Canopy & Shade Mapper

A mapping tool that combines satellite data with local zoning maps to help cities identify urban heat islands and plan where to plant new trees to maximize cooling for vulnerable neighborhoods.

## Data integrity rules

### Claim-level attribution

Every published claim — finding, insight, headline, chart, popup value — carries its **own specific sources** (dataset, provider, vintage, license), attached to the statement itself, never pooled into a single page footer.

> Pairing each claim with its specific sources is what lets a skeptical reader — or a CityLAB data person — verify *one* statement without auditing the whole pipeline. It's the difference between "trust the page" and "check this line."

Rules for any agent working on this project:

1. **New claim ⇒ new attribution.** Any generated statement that contains a number gets a `sources` list naming exactly the datasets that produced that number (see `SRC` in `pipeline/compute_stats.py`). Cite the primary reference for external benchmarks (e.g. Konijnendijk 2022 for 3-30-300), not a secondary article.
2. **Attribution travels with the data, not the markup.** Sources are generated into `stats.json` alongside the claim text; the page only renders them. Never hand-write a source string into HTML.
3. **Enforced, not aspirational.** Tests must fail if a finding/insight ships without sources (`pipeline/tests/test_stats.py`). Extend the test when adding new claim types.
4. **Sibling rule — no hardcoded numbers:** every number on the page comes from a tested artifact (`stats.json`/dataset). Attribution and provenance are two halves of the same contract.

Decision record: `docs/adr/0001-claim-level-attribution.md`.

## Agent skills

### Issue tracker

Issues live as local markdown files under `.scratch/<feature>/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Canonical defaults (needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.
