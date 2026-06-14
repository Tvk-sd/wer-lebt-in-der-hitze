# Wer lebt in der Hitze? (Who lives in the heat?)

**Live: https://wer-lebt-in-der-hitze.vercel.app**

A data story on heat, tree canopy, and social inequality across Berlin's 542
LOR planning units (Planungsräume) — chapter one of the Cooling Island Finder.
Built entirely on Berlin's official open data.

> Key finding: tree canopy strongly predicts daytime heat across Berlin
> (r = −0.90), yet only **19.4 %** of Berliners live in a planning unit that
> meets the 30 %-canopy mark of the 3-30-300 rule. The heat is shared evenly;
> the shade that softens it is not.

The page reads as a scrollytelling feature in German; the analysis, data, and
methodology are published openly so every figure is reproducible.

## Architecture

Three stages with strict contracts — **the page only ever displays numbers
from tested artifacts**, never hardcoded (see `docs/adr/0001-claim-level-attribution.md`):

```
pipeline/build_dataset.py   WFS sources  → site/data/lor_dataset.{geojson,csv}
pipeline/compute_stats.py   dataset      → site/data/stats.json
site/                       static page  → consumes dataset + stats.json only
```

Two heavier per-layer aggregations feed `build_dataset.py` via `data/interim/`:
`pipeline/heat_layer.py` (climate model → per-LOR heat) and
`pipeline/canopy_layer.py` (1×1 m vegetation raster → per-LOR canopy).

## Reproduce

Python 3.11+. Dependencies: `pytest` (tests), `shapely` (geometry),
`rasterio` + `numpy` (canopy raster), `pillow` (social image).

```bash
pip install pytest shapely rasterio numpy pillow

# optional — regenerate the per-layer aggregates (slow: WFS + 785 MB raster):
python3 pipeline/heat_layer.py       # climate model 2022 → data/interim/
python3 pipeline/canopy_layer.py     # vegetation heights 2020 → data/interim/

python3 pipeline/build_dataset.py    # fetch + join LOR + MSS, simplify geometry
python3 pipeline/compute_stats.py    # compute all published statistics
python3 pipeline/make_og_image.py    # social-preview image (optional)
python3 -m pytest                    # contract + golden-number tests
python3 -m http.server -d site 8000  # view at http://localhost:8000
```

The committed `data/interim/*.json` let you rebuild without the slow steps.

## Data sources

| Layer | Source | Vintage |
|---|---|---|
| LOR Planungsräume boundaries | Geoportal Berlin, WFS `lor_2021` | 01.01.2021 |
| Social status (MSS) | SenStadt, WFS `mss_2025` (`si_n` status index) | 2025 (data 12/2024) |
| Heat (PET 14:00, air temp 04:00) | SenStadt Klimamodell Berlin, WFS `ua_klimaanalyse_2022`, area-weighted block→LOR (`pipeline/heat_layer.py`, needs `shapely`) | 2022 |
| Tree canopy (vegetation ≥ 4 m) | Umweltatlas Vegetationshöhen, 1×1m raster (785 MB ATOM download), zonal counts (`pipeline/canopy_layer.py`, needs `rasterio`/`numpy`), DL-DE-Zero | 2020 |

7 of 542 LORs carry no MSS status ("ohne Zuordnung": 6 with fewer than 300
residents, 1 statistical outlier). They remain in the dataset, flagged
`mss_valid = false`.

## Licenses

- **Code** (this repository): MIT — see [`LICENSE`](LICENSE).
- **Source data**: Datenlizenz Deutschland – Namensnennung – 2.0 (Vegetationshöhen:
  DL-DE-Zero-2.0). Attribution: Geoportal Berlin / Senatsverwaltung für
  Stadtentwicklung, Bauen und Wohnen.
- **3-30-300 rule**: Konijnendijk, C.C. (2022), *Journal of Forestry Research*.

## Repository docs

- Domain glossary: `CONTEXT.md`
- Architecture decisions: `docs/adr/`

Product/process documents (PRD, research, findings, tracker) are kept private.
