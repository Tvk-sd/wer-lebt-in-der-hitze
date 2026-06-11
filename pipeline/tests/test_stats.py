"""Tests for the statistics module: hand-computable fixture + golden numbers
against the real stats.json (pinned to the MSS 2025 vintage)."""

import json
from pathlib import Path

import pytest

from compute_stats import compute_stats

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "site" / "data"


def row(plr_id, ew, status, valid=True):
    return {
        "plr_id": plr_id,
        "ew": ew,
        "mss_status_index": status,
        "mss_valid": valid,
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
