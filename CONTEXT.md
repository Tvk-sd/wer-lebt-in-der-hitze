# CONTEXT — Wer lebt in der Hitze? / Cooling Island Finder

Domain glossary for this repo. Use these terms exactly as defined — in code, issues, tests, findings, and narrative copy. Where a term has tempting synonyms, the gloss says which to avoid and why.

## Spatial units

**LOR / Planungsraum** — Berlin's "Lebensweltlich orientierte Räume" planning units, version 01.01.2021; exactly **542** Planungsräume. The study's unit of analysis. *Not* Bezirk (only 12 — averages wash out the signal; decision made explicitly against "income per Bezirk"), *not* Kiez (colloquial, undefined). Key: `plr_id`.

**Block / ISU-Blockfläche** — the ~30–58k block(part) polygons the Umweltatlas products are delivered on (key: `schl5`/`schluessel`). Finer than LOR; aggregated up via area-weighted means. Block level is where heat inequality actually lives ("below the averages") — the premise of chapter two.

## Social dimension

**Sozialstatus / MSS status index** — `si_n` from Monitoring Soziale Stadtentwicklung 2025: 1 hoch, 2 mittel, 3 niedrig, 4 sehr niedrig. The official vulnerability metric. **Do not** paraphrase as "income" or "arm/reich" — MSS is a composite (unemployment, transfer benefits, child poverty). Say "Planungsräume mit niedrigem Sozialstatus", not "arme Viertel".

**ohne Zuordnung / unassigned** — 7 of 542 LORs carry no status (6 under 300 residents, 1 statistical outlier; `kom != "gültig"`, `mss_valid = false`). Kept in the dataset, excluded from status comparisons, always disclosed.

**bevölkerungsgewichtet / population-weighted** — the default aggregation for all published means: weighted by `ew` (residents), because the study asks who *lives* in the heat, not which *area* is hot. State the weighting when reporting means.

## Heat

**PET 14 Uhr (`pet14h`)** — Physiologically Equivalent Temperature at 14:00, the **daytime felt heat stress**. Radiation-driven: peaks include open suburban areas, so high PET ≠ "urban heat island". German label: "Hitzebelastung am Tag" / "gefühlte Temperatur".

**Lufttemperatur 4 Uhr (`t2m04h`)** — air temperature at 04:00, the **nighttime heat island** signal ("nächtliche Wärmeinsel"). This is the canonical UHI metric; use it for center-vs-edge claims. Never mix the two: day and night tell different stories.

**Modellierter autochthoner Sommertag** — all heat values come from a FITNAH 3D simulation (10×10 m, 2022 city structure) of an *average cloudless, low-wind, high-pressure summer day* — **not a measured date**. Phrase findings as structural ("an jedem wolkenlosen Sommertag"), never as event reporting ("während der Hitzewelle 2022").

## Green

**Baumkronen / canopy (`canopy_pct`)** — vegetation **≥ 4 m** height (Vegetationshöhen 2020, 1×1m raster, values in decimeters; threshold `CANOPY_MIN_HEIGHT_M` in `pipeline/canopy_layer.py`), as share of *total* LOR area incl. water and sealed surfaces. This is the protection metric and the policy lever.

**Vegetationsanteil (`veg_pct`)** — any-height vegetation share, incl. grass (>⅓ of Berlin's vegetated area is under 1 m). Context only. **Never** present `veg_pct` as canopy — conflating them was explicitly rejected (that's why the block product wasn't used).

**3-30-300-Regel** — Konijnendijk (2022), Journal of Forestry Research: 3 visible trees, 30% canopy, green space within 300 m. The study uses the **30** component as its external benchmark. Cite the primary reference, not secondary articles.

**Kühle Insel / cooling island** — BaumEntscheid commitment (1,000 cooling islands, ~300k trees). Chapter two — the **Cooling Island Finder** — answers where they should go. In chapter one it appears only as the closing question.

## Editorial & methodology vocabulary

**Befund / finding** — a concrete, named, sourced fact ("3,3 % in Helle Mitte, 75,6 % in Allende II"). Findings carry the narrative.

**Einordnung / insight** — interpretation layered on findings ("Die Hitze ist geteilt, der Schutz nicht"). Never publish an insight whose numbers aren't in a finding or stat.

**Claim-level attribution** — every published claim carries its own `sources` list (dataset, provider, vintage, license; generated in `compute_stats.py`, test-enforced). See ADR 0001. Sibling rule: **no hardcoded numbers** — the page renders only `stats.json`/dataset values.

**Golden numbers** — vintage-pinned test assertions (e.g. 723,172; 19.4%). Deliberately brittle: a new data vintage must break tests and force a conscious republication decision.

## Pipeline stages (architecture vocabulary)

**dataset → stats → story**: `build_dataset.py` joins everything into one 542-row artifact (`site/data/lor_dataset.{geojson,csv}`); `compute_stats.py` derives all published numbers and texts (`stats.json`); the static site renders only those artifacts. Heavy per-layer aggregations (`heat_layer.py`, `canopy_layer.py`) are **interim** steps cached in `data/interim/` (committed) from raw downloads in `data/raw/` (gitignored).
