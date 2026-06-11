"""Stage 1: Fetch LOR boundaries + MSS 2025 social data from Berlin's open WFS
services and join them into the canonical LOR dataset (GeoJSON + CSV).

Outputs to site/data/ — the single source of truth consumed by the stats
module, the story page, and the tests.
"""

import csv
import json
import urllib.request
from datetime import date
from pathlib import Path

USER_AGENT = "wer-lebt-in-der-hitze/0.1 (open data study)"

LOR_WFS = (
    "https://gdi.berlin.de/services/wfs/lor_2021"
    "?service=WFS&version=2.0.0&request=GetFeature"
    "&typenames=lor_2021:a_lor_plr_2021"
    "&outputFormat=application/json&srsName=EPSG:4326"
)
MSS_WFS = (
    "https://gdi.berlin.de/services/wfs/mss_2025"
    "?service=WFS&version=2.0.0&request=GetFeature"
    "&typenames=mss_2025:mss2025_indizes_542"
    "&outputFormat=application/json"
    "&propertyName=plr_id,plr_name,bez_id,ew,si_n,si_v,kom,zeit"
)

OUT_DIR = Path(__file__).resolve().parent.parent / "site" / "data"
HEAT_INTERIM = Path(__file__).resolve().parent.parent / "data" / "interim" / "heat_by_lor.json"
CANOPY_INTERIM = Path(__file__).resolve().parent.parent / "data" / "interim" / "canopy_by_lor.json"

MSS_UNASSIGNED = -9999  # official marker: Planungsraum ohne Zuordnung

CSV_COLUMNS = [
    "plr_id", "plr_name", "bzr_name", "pgr_name", "bez_id", "bez_name",
    "ew", "mss_status_index", "mss_status_class", "mss_valid",
    "pet14h", "t2m04h", "canopy_pct", "veg_pct",
]


def fetch_geojson(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.load(resp)


def round_coords(obj, ndigits=5):
    """Round nested coordinate arrays to ~1m precision to keep the file small."""
    if isinstance(obj, float):
        return round(obj, ndigits)
    if isinstance(obj, list):
        return [round_coords(item, ndigits) for item in obj]
    return obj


def load_interim(path):
    """Per-LOR metrics from a stage-1b script (heat_layer.py / canopy_layer.py)."""
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))["by_lor"]


def join_features(lor_fc, mss_fc, heat_by_lor=None, canopy_by_lor=None):
    """Join LOR boundary features with MSS rows on plr_id, plus heat metrics
    (issue 03) when available.

    Raises ValueError if any LOR has no MSS row (the join must be total —
    a partial join means the data vintages no longer match).
    """
    heat_by_lor = heat_by_lor or {}
    canopy_by_lor = canopy_by_lor or {}
    mss_by_id = {f["properties"]["plr_id"]: f["properties"] for f in mss_fc["features"]}
    features = []
    missing = []
    for f in lor_fc["features"]:
        lor = f["properties"]
        mss = mss_by_id.get(lor["plr_id"])
        if mss is None:
            missing.append(lor["plr_id"])
            continue
        bez_id, _, bez_name = lor["bez"].partition(" - ")
        si_n = mss.get("si_n")
        unassigned = si_n is None or int(si_n) == MSS_UNASSIGNED
        heat = heat_by_lor.get(lor["plr_id"], {})
        canopy = canopy_by_lor.get(lor["plr_id"], {})
        features.append({
            "type": "Feature",
            "geometry": round_coords(f["geometry"]),
            "properties": {
                "plr_id": lor["plr_id"],
                "plr_name": lor["plr_name"],
                "bzr_name": lor["bzr_name"],
                "pgr_name": lor["pgr_name"],
                "bez_id": bez_id,
                "bez_name": bez_name,
                "ew": mss.get("ew"),
                "mss_status_index": None if unassigned else int(si_n),
                "mss_status_class": mss.get("si_v"),
                "mss_valid": mss.get("kom") == "gültig",
                "pet14h": heat.get("pet14h"),
                "t2m04h": heat.get("t2m04h"),
                "canopy_pct": canopy.get("canopy_pct"),
                "veg_pct": canopy.get("veg_pct"),
            },
        })
    if missing:
        raise ValueError(f"{len(missing)} LORs without MSS row: {missing[:5]}")
    features.sort(key=lambda f: f["properties"]["plr_id"])
    return {
        "type": "FeatureCollection",
        "metadata": {
            "title": "Wer lebt in der Hitze? — LOR-Basisdatensatz",
            "sources": {
                "lor": "Geoportal Berlin / Lebensweltlich orientierte Räume (LOR) 01.01.2021, WFS lor_2021",
                "mss": "SenStadt / Monitoring Soziale Stadtentwicklung 2025, WFS mss_2025 (Datenstand 2024-12)",
                "heat": "SenStadt / Klimamodell Berlin: Klimaanalysekarten 2022, WFS ua_klimaanalyse_2022 (PET 14 Uhr, Lufttemperatur 4 Uhr; flächengewichtetes Mittel je LOR)",
                "canopy": "SenStadt / Vegetationshöhen 2020 (Umweltatlas), 1×1m-Raster; Baumkronen = Vegetation ≥ 4 m, Anteil an der LOR-Gesamtfläche",
            },
            "license": "Datenlizenz Deutschland – Namensnennung – Version 2.0",
            "generated": date.today().isoformat(),
        },
        "features": features,
    }


def write_outputs(dataset, out_dir=OUT_DIR):
    out_dir.mkdir(parents=True, exist_ok=True)
    geojson_path = out_dir / "lor_dataset.geojson"
    with geojson_path.open("w", encoding="utf-8") as fh:
        json.dump(dataset, fh, ensure_ascii=False, separators=(",", ":"))
    csv_path = out_dir / "lor_dataset.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for f in dataset["features"]:
            writer.writerow(f["properties"])
    return geojson_path, csv_path


def main():
    print("Fetching LOR boundaries …")
    lor_fc = fetch_geojson(LOR_WFS)
    print(f"  {len(lor_fc['features'])} LOR features")
    print("Fetching MSS 2025 indices …")
    mss_fc = fetch_geojson(MSS_WFS)
    print(f"  {len(mss_fc['features'])} MSS rows")
    heat = load_interim(HEAT_INTERIM)
    print(f"Heat metrics: {'loaded for ' + str(len(heat)) + ' LORs' if heat else 'not available (run heat_layer.py)'}")
    canopy = load_interim(CANOPY_INTERIM)
    print(f"Canopy metrics: {'loaded for ' + str(len(canopy)) + ' LORs' if canopy else 'not available (run canopy_layer.py)'}")
    dataset = join_features(lor_fc, mss_fc, heat, canopy)
    geojson_path, csv_path = write_outputs(dataset)
    size_mb = geojson_path.stat().st_size / 1e6
    print(f"Wrote {geojson_path} ({size_mb:.1f} MB) and {csv_path}")


if __name__ == "__main__":
    main()
