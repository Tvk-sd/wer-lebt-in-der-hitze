"""Contract tests for the built LOR dataset (site/data/lor_dataset.geojson).

These run against the real pipeline output — run pipeline/build_dataset.py
first. They pin facts observed in the official data (vintage MSS 2025);
if a source vintage changes, these tests fail loudly, which is intended.
"""

import csv
import json
from pathlib import Path

import pytest

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "site" / "data"

BERLIN_BBOX = (12.9, 52.3, 13.8, 52.7)  # lon_min, lat_min, lon_max, lat_max


@pytest.fixture(scope="module")
def dataset():
    path = DATA_DIR / "lor_dataset.geojson"
    if not path.exists():
        pytest.fail("Dataset missing — run pipeline/build_dataset.py first")
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def rows(dataset):
    return [f["properties"] for f in dataset["features"]]


def test_exactly_542_lors(rows):
    assert len(rows) == 542


def test_plr_ids_unique(rows):
    ids = [r["plr_id"] for r in rows]
    assert len(set(ids)) == 542


def test_no_nulls_in_core_columns(rows):
    for r in rows:
        for col in ("plr_id", "plr_name", "bez_id", "bez_name", "mss_status_class"):
            assert r[col], f"null/empty {col} in {r['plr_id']}"


def test_mss_exclusions_handled(rows):
    """MSS 2025: 535 valid LORs, 7 invalid (6 under 300 residents, 1 outlier).
    Invalid/unassigned rows stay in the dataset but carry no status index."""
    assert sum(1 for r in rows if r["mss_valid"]) == 535
    unassigned = [r for r in rows if r["mss_status_index"] is None]
    assert len(unassigned) == 7
    for r in unassigned:
        assert not r["mss_valid"]


def test_status_index_domain(rows):
    assigned = {r["mss_status_index"] for r in rows if r["mss_status_index"] is not None}
    assert assigned == {1, 2, 3, 4}


def test_population_plausible(rows):
    total = sum(r["ew"] or 0 for r in rows)
    assert 3_000_000 < total < 4_500_000


def test_geometries_within_berlin(dataset):
    lon_min, lat_min, lon_max, lat_max = BERLIN_BBOX

    def check(coords):
        if isinstance(coords[0], (int, float)):
            lon, lat = coords[0], coords[1]
            assert lon_min < lon < lon_max and lat_min < lat < lat_max
        else:
            for c in coords:
                check(c)

    for f in dataset["features"]:
        check(f["geometry"]["coordinates"])


def test_heat_columns_complete(rows):
    """Issue 03: every LOR carries both heat metrics (Klimamodell 2022)."""
    for r in rows:
        assert r["pet14h"] is not None, f"pet14h missing for {r['plr_id']}"
        assert r["t2m04h"] is not None, f"t2m04h missing for {r['plr_id']}"


def test_heat_values_within_model_bounds(rows):
    for r in rows:
        assert 20.0 < r["pet14h"] < 45.0, f"pet14h out of bounds: {r['plr_id']}"
        assert 10.0 < r["t2m04h"] < 25.0, f"t2m04h out of bounds: {r['plr_id']}"


def test_dense_center_hotter_than_forest_edge(rows):
    """Nighttime urban heat island: dense central Stülerstraße (Mitte) must rank
    hotter than forest-edge Schmöckwitz/Rauchfangswerder (Treptow-Köpenick).
    Nighttime air temperature is the canonical UHI signal; daytime PET also
    differs here but is radiation-driven and peaks in open suburban areas."""
    by_name = {r["plr_name"]: r for r in rows}
    center = by_name["Stülerstraße"]
    edge = by_name["Schmöckwitz/Rauchfangswerder"]
    assert center["t2m04h"] > edge["t2m04h"]
    assert center["pet14h"] > edge["pet14h"]


def test_canopy_columns_complete_and_bounded(rows):
    """Issue 02: every LOR carries canopy + vegetation share within 0–100,
    and canopy (>=4m) can never exceed total vegetation share."""
    for r in rows:
        assert r["canopy_pct"] is not None, f"canopy_pct missing for {r['plr_id']}"
        assert 0 <= r["canopy_pct"] <= 100
        assert 0 <= r["veg_pct"] <= 100
        assert r["canopy_pct"] <= r["veg_pct"] + 0.1


def test_forest_edge_greener_than_dense_center(rows):
    """Forest-edge Schmöckwitz/Rauchfangswerder must have far more canopy
    than dense central Stülerstraße."""
    by_name = {r["plr_name"]: r for r in rows}
    assert by_name["Schmöckwitz/Rauchfangswerder"]["canopy_pct"] > 2 * by_name["Stülerstraße"]["canopy_pct"]


def test_csv_matches_geojson(rows):
    path = DATA_DIR / "lor_dataset.csv"
    assert path.exists(), "CSV missing — run pipeline/build_dataset.py first"
    with path.open(encoding="utf-8") as fh:
        csv_rows = list(csv.DictReader(fh))
    assert len(csv_rows) == len(rows)
    assert {r["plr_id"] for r in csv_rows} == {r["plr_id"] for r in rows}
