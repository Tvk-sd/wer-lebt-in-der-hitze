# Wer lebt in der Hitze?

A data story on heat, tree canopy, and social inequality across Berlin's 542
LOR planning units (Planungsräume) — chapter one of the Cooling Island Finder.

Built entirely on Berlin's official open data (Geoportal WFS services).

## Pipeline

Three stages with strict contracts — the page only ever displays numbers from
tested artifacts:

```
pipeline/build_dataset.py   WFS sources → site/data/lor_dataset.{geojson,csv}
pipeline/compute_stats.py   dataset     → site/data/stats.json
site/                       static page → consumes dataset + stats.json only
```

## Run it

Requires Python 3.11+ (standard library only; `pytest` for tests).

```bash
python3 pipeline/build_dataset.py    # fetch + join LOR boundaries and MSS 2025
python3 pipeline/compute_stats.py    # compute published statistics
python3 -m pytest                    # contract + golden-number tests
python3 -m http.server -d site 8000  # view at http://localhost:8000
```

## Data sources

| Layer | Source | Vintage |
|---|---|---|
| LOR Planungsräume boundaries | Geoportal Berlin, WFS `lor_2021` | 01.01.2021 |
| Social status (MSS) | SenStadt, WFS `mss_2025` (`si_n` status index) | 2025 (data 12/2024) |
| Heat (PET 14:00, air temp 04:00) | SenStadt Klimamodell Berlin, WFS `ua_klimaanalyse_2022`, area-weighted block→LOR (`pipeline/heat_layer.py`, needs `shapely`) | 2022 |

License of source data: Datenlizenz Deutschland – Namensnennung – 2.0.

7 of 542 LORs carry no MSS status ("ohne Zuordnung": 6 with fewer than 300
residents, 1 statistical outlier). They remain in the dataset, flagged
`mss_valid = false`.

## Project docs

- PRD: `.scratch/wer-lebt-in-der-hitze/PRD.md`
- Research: `docs/research/`
- Parked side-project concepts: `docs/concepts/side-projects.md`
