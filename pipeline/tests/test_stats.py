"""Tests for the statistics module: hand-computable fixture + golden numbers
against the real stats.json (pinned to the MSS 2025 vintage)."""

import json
from pathlib import Path

import pytest

from compute_stats import compute_stats

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "site" / "data"


def row(plr_id, ew, status, valid=True, pet14h=None, t2m04h=None, canopy_pct=None):
    return {
        "plr_id": plr_id,
        "ew": ew,
        "mss_status_index": status,
        "mss_valid": valid,
        "pet14h": pet14h,
        "t2m04h": t2m04h,
        "canopy_pct": canopy_pct,
    }


def test_compute_stats_on_miniature_fixture():
    rows = [
        row("01", 1000, 1),
        row("02", 2000, 2),
        row("03", 3000, 3),
        row("04", 4000, 4),
        row("05", 0, None, valid=False),
    ]
    stats = compute_stats(rows)
    assert stats["total_lors"] == 5
    assert stats["valid_lors"] == 4
    assert stats["unassigned_lors"] == 1
    assert stats["total_population"] == 10_000
    # disadvantaged = status 3 + 4 = 7000 of 10000 = 70.0%
    assert stats["headline"]["disadvantaged_population"] == 7_000
    assert stats["headline"]["disadvantaged_pop_share_pct"] == 70.0
    mittel = next(g for g in stats["by_status"] if g["index"] == 2)
    assert mittel == {
        "index": 2, "class": "mittel", "lors": 1,
        "population": 2000, "pop_share_pct": 20.0,
    }


def test_population_weighted_heat_means():
    """Hand-computed: heat means weighted by people, not by LOR count."""
    rows = [
        row("01", 1000, 1, pet14h=30.0, t2m04h=16.0),
        row("02", 1000, 4, pet14h=36.0, t2m04h=18.0),
        row("03", 3000, 4, pet14h=40.0, t2m04h=19.0),
    ]
    stats = compute_stats(rows)
    s4 = next(g for g in stats["by_status"] if g["index"] == 4)
    # (1000*36 + 3000*40) / 4000 = 39.0 ; (1000*18 + 3000*19) / 4000 = 18.75
    assert s4["pet14h_mean"] == 39.0
    assert s4["t2m04h_mean"] == 18.75
    assert stats["heat"]["pet14h_gap_lowest_vs_highest_status"] == 9.0
    assert stats["heat"]["t2m04h_gap_lowest_vs_highest_status"] == 2.75
    # berlin-wide: (1000*30 + 1000*36 + 3000*40) / 5000 = 37.2
    assert stats["heat"]["berlin_pet14h_mean"] == 37.2


def test_stats_without_heat_columns():
    """Stats must still work on a dataset built before heat_layer.py ran."""
    stats = compute_stats([row("01", 1000, 1), row("02", 1000, 4)])
    assert stats["heat"] is None
    assert stats["canopy"] is None
    assert "pet14h_mean" not in stats["by_status"][0]


def test_canopy_stats_on_fixture():
    """Hand-computed: gap, 30%-rule population share."""
    rows = [
        row("01", 1000, 1, canopy_pct=40.0),  # meets 30% rule
        row("02", 1000, 4, canopy_pct=20.0),
        row("03", 3000, 4, canopy_pct=30.0),  # meets 30% rule
    ]
    stats = compute_stats(rows)
    s4 = next(g for g in stats["by_status"] if g["index"] == 4)
    # (1000*20 + 3000*30) / 4000 = 27.5 ; gap = 40 - 27.5 = 12.5
    assert s4["canopy_pct_mean"] == 27.5
    assert stats["canopy"]["canopy_gap_highest_vs_lowest_status"] == 12.5
    # population in LORs >= 30%: 1000 + 3000 of 5000 = 80%
    assert stats["canopy"]["pop_in_lor_canopy_30plus"] == 4000
    assert stats["canopy"]["pop_share_canopy_30plus_pct"] == 80.0


def test_golden_numbers_mss_2025():
    """Pinned to MSS 2025 (Datenstand 2024-12). Fails loudly on vintage change."""
    path = DATA_DIR / "stats.json"
    if not path.exists():
        pytest.fail("stats.json missing — run pipeline/compute_stats.py first")
    stats = json.loads(path.read_text(encoding="utf-8"))
    assert stats["total_lors"] == 542
    assert stats["valid_lors"] == 535
    assert stats["total_population"] == 3_897_145
    assert stats["headline"]["disadvantaged_population"] == 723_172
    assert stats["headline"]["disadvantaged_pop_share_pct"] == 18.6
    # heat layer, pinned to Klimamodell Berlin 2022 (issue 03)
    assert stats["heat"]["berlin_pet14h_mean"] == 35.22
    assert stats["heat"]["berlin_t2m04h_mean"] == 17.85
    assert stats["heat"]["pet14h_gap_lowest_vs_highest_status"] == 0.67
    assert stats["heat"]["t2m04h_gap_lowest_vs_highest_status"] == 0.31
    # canopy layer, pinned to Vegetationshöhen 2020, threshold 4m (issue 02)
    assert stats["canopy"]["berlin_canopy_pct_mean"] == 24.67
    assert stats["canopy"]["canopy_gap_highest_vs_lowest_status"] == 6.34
    assert stats["canopy"]["pop_in_lor_canopy_30plus"] == 755_469
    assert stats["canopy"]["pop_share_canopy_30plus_pct"] == 19.4
    # generated insights: present, and numbers inside the text match the data
    ids = [i["id"] for i in stats["insights"]]
    assert ids == ["heat-shared", "canopy-divided", "rule-30", "below-average"]
    assert "19,4 %" in stats["insights"][2]["text_de"]
    assert "755.469" in stats["insights"][2]["text_de"]
    assert "6,34 Prozentpunkten" in stats["insights"][1]["text_de"]
