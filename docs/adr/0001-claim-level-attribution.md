# ADR 0001: Claim-level source attribution for published statements

**Status:** accepted (2026-06-11)
**Context:** "Wer lebt in der Hitze?" data study; applies to all data-related work in this repo, including the future Cooling Island Finder.

## Context

The study publishes findings and insights built from multiple official datasets with different providers, vintages, and licenses (LOR 2021, MSS 2025, Klimamodell 2022, Vegetationshöhen 2020). The audience — CityLAB/Technologiestiftung data practitioners, journalists, district officials — is professionally skeptical. A single "data sources" footer forces such a reader to audit the entire pipeline to verify any one statement, because nothing says *which* dataset produced *which* number.

The project already enforces "no hardcoded numbers on the page" (every displayed value comes from the golden-tested `stats.json`). Provenance was the missing half of that contract.

## Decision

Every published claim carries its own specific source list, attached to the statement:

- **Granularity:** per claim, not per page. A canopy fact cites Vegetationshöhen; a per-status fact additionally cites MSS; an external benchmark (30% canopy) cites its primary academic reference (Konijnendijk 2022), not a secondary article.
- **Mechanism:** source labels live in code (`SRC` dict in `pipeline/compute_stats.py`) and are generated into `stats.json` as `findings[].sources` / `insights[].sources`. The page renders them beneath each statement ("Quellen: …"). Markdown docs mirror them per item.
- **Enforcement:** a test fails if any finding or insight ships without sources, or with an unrecognized provider. New claim types must extend this test.

## Consequences

- A reader can verify one statement in isolation — "check this line" instead of "trust the page". This is a credibility feature aimed directly at the project's target audience.
- Adding a claim costs one extra line (the sources list); forgetting it breaks CI rather than shipping silently.
- Source labels are maintained in one place; renaming a dataset vintage updates every attribution consistently.
- The pattern is reusable for chapter two (Cooling Island Finder), where site-ranking claims will combine even more layers and provenance will matter more, not less.

## Related

- Sibling principle: no hardcoded numbers on the page (PRD, `.scratch/wer-lebt-in-der-hitze/PRD.md` — Implementation Decisions).
- Full source registry: `docs/sources.md`.
