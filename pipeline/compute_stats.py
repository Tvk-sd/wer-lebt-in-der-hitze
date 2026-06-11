"""Stage 2: Compute the published statistics from the LOR dataset.

Consumes ONLY site/data/lor_dataset.geojson and emits site/data/stats.json.
The story page may display numbers from stats.json exclusively — never
hardcoded, never from raw data.
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "site" / "data"

STATUS_CLASSES = {1: "hoch", 2: "mittel", 3: "niedrig", 4: "sehr niedrig"}
DISADVANTAGED = (3, 4)  # niedrig + sehr niedrig


def pop_weighted_mean(rows, key):
    """Population-weighted mean of `key` over rows that have a value.
    Weighted by people, not area — the study asks who LIVES in the heat."""
    pairs = [(r["ew"] or 0, r[key]) for r in rows if r.get(key) is not None]
    total = sum(ew for ew, _ in pairs)
    if total == 0:
        return None
    return round(sum(ew * v for ew, v in pairs) / total, 2)


def compute_stats(rows):
    """rows: list of property dicts from the LOR dataset features."""
    total_population = sum(r["ew"] or 0 for r in rows)
    has_heat = any(r.get("pet14h") is not None for r in rows)
    by_status = []
    for index, label in STATUS_CLASSES.items():
        group = [r for r in rows if r["mss_status_index"] == index]
        pop = sum(r["ew"] or 0 for r in group)
        entry = {
            "index": index,
            "class": label,
            "lors": len(group),
            "population": pop,
            "pop_share_pct": round(100 * pop / total_population, 1),
        }
        if has_heat:
            entry["pet14h_mean"] = pop_weighted_mean(group, "pet14h")
            entry["t2m04h_mean"] = pop_weighted_mean(group, "t2m04h")
        by_status.append(entry)
    unassigned = [r for r in rows if r["mss_status_index"] is None]
    disadvantaged_pop = sum(
        g["population"] for g in by_status if g["index"] in DISADVANTAGED
    )
    heat = None
    if has_heat:
        lowest = next(g for g in by_status if g["index"] == 4)
        highest = next(g for g in by_status if g["index"] == 1)
        heat = {
            "berlin_pet14h_mean": pop_weighted_mean(rows, "pet14h"),
            "berlin_t2m04h_mean": pop_weighted_mean(rows, "t2m04h"),
            "t2m04h_gap_lowest_vs_highest_status": round(
                lowest["t2m04h_mean"] - highest["t2m04h_mean"], 2
            ),
            "pet14h_gap_lowest_vs_highest_status": round(
                lowest["pet14h_mean"] - highest["pet14h_mean"], 2
            ),
            "note": (
                "Mittelwerte bevölkerungsgewichtet. PET 14 Uhr = Hitzebelastung "
                "am Tag (strahlungsdominiert), Lufttemperatur 4 Uhr = nächtliche "
                "Wärmeinsel. Quelle: Klimamodell Berlin 2022."
            ),
        }
    return {
        "total_lors": len(rows),
        "valid_lors": sum(1 for r in rows if r["mss_valid"]),
        "unassigned_lors": len(unassigned),
        "total_population": total_population,
        "by_status": by_status,
        "heat": heat,
        "headline": {
            "disadvantaged_population": disadvantaged_pop,
            "disadvantaged_pop_share_pct": round(
                100 * disadvantaged_pop / total_population, 1
            ),
            "text_de": (
                f"{disadvantaged_pop:,}".replace(",", ".")
                + " Berliner:innen leben in Planungsräumen mit niedrigem "
                  "oder sehr niedrigem Sozialstatus — "
                + str(round(100 * disadvantaged_pop / total_population, 1)).replace(".", ",")
                + " % der Stadt."
            ),
        },
    }


def main():
    dataset = json.loads((DATA_DIR / "lor_dataset.geojson").read_text(encoding="utf-8"))
    rows = [f["properties"] for f in dataset["features"]]
    stats = compute_stats(rows)
    stats["meta"] = dataset.get("metadata", {})
    out = DATA_DIR / "stats.json"
    out.write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Wrote {out}")
    print("Headline:", stats["headline"]["text_de"])


if __name__ == "__main__":
    main()
