"""Issue 03: Aggregate the Umweltatlas Klimaanalysekarten 2022 (block-level
vector model) to LOR level.

Computes area-weighted means per LOR for:
  - pet14h   : Physiologically Equivalent Temperature at 14:00 [°C] (daytime heat stress)
  - t2m04h   : air temperature at 04:00 [°C] (nighttime heat indicator)

Raw WFS downloads are cached in data/raw/ (gitignored, ~100+ MB).
Output: data/interim/heat_by_lor.json — merged into the dataset by
build_dataset.py. All geometry work happens in EPSG:25833 (meters).

Source: Geoportal Berlin, WFS ua_klimaanalyse_2022 (Klimamodell Berlin 2022,
10m grid aggregated to ISU blocks by SenStadt). Documented choice: we use the
block-level vector product, not the raster, because it is the official
planning-grade aggregation and avoids raster processing entirely.
"""

import json
import urllib.request
from pathlib import Path

from shapely import STRtree
from shapely.geometry import shape

USER_AGENT = "wer-lebt-in-der-hitze/0.1 (open data study)"
ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
INTERIM_DIR = ROOT / "data" / "interim"

WFS_BASE = (
    "https://gdi.berlin.de/services/wfs/ua_klimaanalyse_2022"
    "?service=WFS&version=2.0.0&request=GetFeature"
    "&typenames=ua_klimaanalyse_2022:{layer}"
    "&outputFormat=application/json&srsName=EPSG:25833"
    "&count={count}&startIndex={start}"
)
LOR_WFS_25833 = (
    "https://gdi.berlin.de/services/wfs/lor_2021"
    "?service=WFS&version=2.0.0&request=GetFeature"
    "&typenames=lor_2021:a_lor_plr_2021"
    "&outputFormat=application/json&srsName=EPSG:25833"
)

# {metric: (attribute, [layers per land-use class: settlement, traffic, green])}
METRICS = {
    "pet14h": ("pet14h", [
        "pa_ua_pet_siedlg_2022", "pb_ua_pet_str_2022", "pc_ua_pet_grfrei_2022",
    ]),
    "t2m04h": ("t2m04h", [
        "fa_ua_lufttemp_siedlg_t2m_04h_2022",
        "fb_ua_lufttemp_str_t2m_04h_2022",
        "fc_ua_lufttemp_grfrei_t2m_04h_2022",
    ]),
}
PAGE_SIZE = 10_000


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.load(resp)


def fetch_layer_cached(layer):
    """Fetch all features of a WFS layer, paged, with a local file cache."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    cache = RAW_DIR / f"{layer}.geojson"
    if cache.exists():
        print(f"  {layer}: cached")
        return json.loads(cache.read_text(encoding="utf-8"))
    features = []
    start = 0
    while True:
        page = fetch_json(WFS_BASE.format(layer=layer, count=PAGE_SIZE, start=start))
        got = page.get("features", [])
        features.extend(got)
        print(f"  {layer}: {len(features)} features …")
        if len(got) < PAGE_SIZE:
            break
        start += PAGE_SIZE
    fc = {"type": "FeatureCollection", "features": features}
    cache.write_text(json.dumps(fc, separators=(",", ":")), encoding="utf-8")
    return fc


def valid(geom):
    return geom if geom.is_valid else geom.buffer(0)


def aggregate_metric(lor_geoms, lor_ids, attribute, layers):
    """Area-weighted mean of `attribute` per LOR across all block layers."""
    weighted = {pid: 0.0 for pid in lor_ids}
    areas = {pid: 0.0 for pid in lor_ids}
    tree = STRtree(lor_geoms)
    for layer in layers:
        fc = fetch_layer_cached(layer)
        for f in fc["features"]:
            value = f["properties"].get(attribute)
            if value is None:
                continue
            block = valid(shape(f["geometry"]))
            for idx in tree.query(block):
                inter = lor_geoms[idx].intersection(block)
                if not inter.is_empty:
                    a = inter.area
                    pid = lor_ids[idx]
                    weighted[pid] += a * float(value)
                    areas[pid] += a
    return {
        pid: round(weighted[pid] / areas[pid], 2) if areas[pid] > 0 else None
        for pid in lor_ids
    }, areas


def main():
    print("Fetching LOR boundaries (EPSG:25833) …")
    lor_fc = fetch_json(LOR_WFS_25833)
    lor_ids = [f["properties"]["plr_id"] for f in lor_fc["features"]]
    lor_geoms = [valid(shape(f["geometry"])) for f in lor_fc["features"]]
    lor_areas = {pid: g.area for pid, g in zip(lor_ids, lor_geoms)}
    print(f"  {len(lor_ids)} LORs")

    result = {pid: {} for pid in lor_ids}
    for metric, (attribute, layers) in METRICS.items():
        print(f"Aggregating {metric} …")
        values, covered = aggregate_metric(lor_geoms, lor_ids, attribute, layers)
        for pid in lor_ids:
            result[pid][metric] = values[pid]
            result[pid][f"{metric}_coverage_pct"] = round(
                100 * covered[pid] / lor_areas[pid], 1
            )

    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    out = INTERIM_DIR / "heat_by_lor.json"
    payload = {
        "source": "Geoportal Berlin, WFS ua_klimaanalyse_2022 (Klimamodell Berlin 2022)",
        "method": "area-weighted mean over ISU block polygons (settlement, traffic, green/open), EPSG:25833",
        "metrics": {
            "pet14h": "PET 14:00 [°C], daytime heat stress",
            "t2m04h": "air temperature 04:00 [°C], nighttime heat indicator",
        },
        "by_lor": result,
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    missing = [pid for pid in lor_ids if result[pid]["pet14h"] is None]
    print(f"Wrote {out} — {len(lor_ids) - len(missing)} LORs with PET, {len(missing)} without: {missing}")


if __name__ == "__main__":
    main()
