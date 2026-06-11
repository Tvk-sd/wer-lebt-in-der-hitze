"""Issue 02: Compute tree canopy cover per LOR from the Vegetationshöhen 2020
raster (1×1m vegetation heights, Umweltatlas, DL-DE-Zero).

Definition (documented methodological choice):
  canopy = vegetation with height >= CANOPY_MIN_HEIGHT_M (default 4 m,
  distinguishing trees from shrubs/lawn; raster stores DECIMETERS).
  canopy_pct = canopy pixels / all pixels inside the LOR polygon (i.e. share
  of total district area incl. water and sealed surfaces).
  veg_pct = share of any-height vegetation, for context.

Raster facts (veg_hoehe_2020_nodata.tif): 45786×37741 px, uint16, EPSG:25833,
nodata=65535. Non-vegetated ground is nodata, so nodata must be excluded from
numerators but counts in the area denominator.

Input : data/raw/veghoehe_2020.zip (785 MB, ATOM download, cached)
Output: data/interim/canopy_by_lor.json — merged by build_dataset.py.
"""

import json
import urllib.request
from pathlib import Path

import numpy as np
import rasterio
from rasterio import features
from rasterio.windows import Window
from shapely import STRtree, box
from shapely.geometry import shape

USER_AGENT = "wer-lebt-in-der-hitze/0.1 (open data study)"
ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
INTERIM_DIR = ROOT / "data" / "interim"

RASTER = f"zip://{RAW_DIR}/veghoehe_2020.zip!veg_hoehe_2020_nodata.tif"
NODATA = 65535

CANOPY_MIN_HEIGHT_M = 4.0  # the single configurable threshold
HEIGHT_UNITS_PER_M = 10    # raster values are decimeters

LOR_WFS_25833 = (
    "https://gdi.berlin.de/services/wfs/lor_2021"
    "?service=WFS&version=2.0.0&request=GetFeature"
    "&typenames=lor_2021:a_lor_plr_2021"
    "&outputFormat=application/json&srsName=EPSG:25833"
)
STRIP_ROWS = 2048  # process the raster in horizontal strips (~190 MB each)


def fetch_lor_cached():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    cache = RAW_DIR / "lor_plr_25833.geojson"
    if not cache.exists():
        req = urllib.request.Request(LOR_WFS_25833, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=300) as resp:
            cache.write_bytes(resp.read())
    return json.loads(cache.read_text(encoding="utf-8"))


def main():
    lor_fc = fetch_lor_cached()
    lor_ids = [f["properties"]["plr_id"] for f in lor_fc["features"]]
    geoms = [shape(f["geometry"]) for f in lor_fc["features"]]
    geoms = [g if g.is_valid else g.buffer(0) for g in geoms]
    tree = STRtree(geoms)
    n = len(lor_ids)
    print(f"{n} LORs")

    threshold = int(CANOPY_MIN_HEIGHT_M * HEIGHT_UNITS_PER_M)
    total_px = np.zeros(n + 1, dtype=np.int64)   # index 0 = outside any LOR
    veg_px = np.zeros(n + 1, dtype=np.int64)
    canopy_px = np.zeros(n + 1, dtype=np.int64)

    with rasterio.open(RASTER) as src:
        for row_off in range(0, src.height, STRIP_ROWS):
            h = min(STRIP_ROWS, src.height - row_off)
            window = Window(0, row_off, src.width, h)
            transform = src.window_transform(window)
            bounds = rasterio.windows.bounds(window, src.transform)
            hits = tree.query(box(*bounds))
            if len(hits) == 0:
                continue
            band = src.read(1, window=window)
            ids = features.rasterize(
                ((geoms[i], i + 1) for i in hits),
                out_shape=(h, src.width),
                transform=transform,
                fill=0,
                dtype="uint32",
            )
            inside = ids > 0
            is_veg = inside & (band != NODATA)
            total_px += np.bincount(ids[inside], minlength=n + 1)
            veg_px += np.bincount(ids[is_veg], minlength=n + 1)
            canopy_px += np.bincount(
                ids[is_veg & (band >= threshold)], minlength=n + 1
            )
            print(f"  rows {row_off}–{row_off + h} done ({len(hits)} LORs touched)")

    by_lor = {}
    for i, pid in enumerate(lor_ids):
        t = int(total_px[i + 1])
        by_lor[pid] = {
            "canopy_pct": round(100 * int(canopy_px[i + 1]) / t, 1) if t else None,
            "veg_pct": round(100 * int(veg_px[i + 1]) / t, 1) if t else None,
        }

    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    out = INTERIM_DIR / "canopy_by_lor.json"
    payload = {
        "source": "Geoportal Berlin / Vegetationshöhen 2020 (Umweltatlas), 1×1m raster, DL-DE-Zero-2.0",
        "method": (
            f"canopy = vegetation height >= {CANOPY_MIN_HEIGHT_M} m (raster in dm); "
            "share of total LOR area (incl. water/sealed); zonal count on EPSG:25833 grid"
        ),
        "canopy_min_height_m": CANOPY_MIN_HEIGHT_M,
        "by_lor": by_lor,
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    vals = [v["canopy_pct"] for v in by_lor.values() if v["canopy_pct"] is not None]
    print(f"Wrote {out}")
    print(f"canopy_pct: min {min(vals)}  median {sorted(vals)[len(vals)//2]}  max {max(vals)}  (n={len(vals)})")


if __name__ == "__main__":
    main()
