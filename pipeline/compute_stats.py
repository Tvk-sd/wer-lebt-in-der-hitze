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


def de(value):
    """German number formatting: 6.34 -> '6,34', 755469 -> '755.469'."""
    if isinstance(value, int):
        return f"{value:,}".replace(",", ".")
    return f"{value:,}".translate(str.maketrans(",.", ".,"))


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
    has_canopy = any(r.get("canopy_pct") is not None for r in rows)
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
        if has_canopy:
            entry["canopy_pct_mean"] = pop_weighted_mean(group, "canopy_pct")
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
                "Die Werte beziehen sich nicht auf einen realen Messtag, sondern auf "
                "einen modellierten durchschnittlichen autochthonen Sommertag: wolkenlos, "
                "windschwach, Hochdruckwetterlage — die Bedingungen, unter denen sich der "
                "städtische Wärmeinseleffekt am stärksten ausprägt. Simulation: FITNAH 3D "
                "(10×10 m) auf Basis der Stadtstruktur 2022, im Auftrag von SenStadt. "
                "PET 14 Uhr = Hitzebelastung am Tag (strahlungsdominiert), Lufttemperatur "
                "4 Uhr = nächtliche Wärmeinsel. Mittelwerte bevölkerungsgewichtet."
            ),
        }
    canopy = None
    if has_canopy:
        lowest = next(g for g in by_status if g["index"] == 4)
        highest = next(g for g in by_status if g["index"] == 1)
        pop_30plus = sum(
            r["ew"] or 0 for r in rows
            if r.get("canopy_pct") is not None and r["canopy_pct"] >= 30
        )
        canopy = {
            "berlin_canopy_pct_mean": pop_weighted_mean(rows, "canopy_pct"),
            "canopy_gap_highest_vs_lowest_status": round(
                highest["canopy_pct_mean"] - lowest["canopy_pct_mean"], 2
            ),
            "pop_in_lor_canopy_30plus": pop_30plus,
            "pop_share_canopy_30plus_pct": round(
                100 * pop_30plus / total_population, 1
            ),
            "note": (
                "Baumkronenanteil = Vegetation ab 4 m Höhe (Vegetationshöhen 2020, "
                "1×1m-Laserscan-Raster) als Anteil an der gesamten LOR-Fläche. "
                "Die 30-%-Marke entspricht der 3-30-300-Regel für gesundes Stadtgrün. "
                "Mittelwerte bevölkerungsgewichtet."
            ),
        }
    findings = []
    if canopy:
        s = {g["index"]: g for g in by_status}
        rated = [g for g in by_status if g["canopy_pct_mean"] is not None]
        least = min(rated, key=lambda g: g["canopy_pct_mean"])
        crows = [r for r in rows if r.get("canopy_pct") is not None]
        cmin = min(crows, key=lambda r: r["canopy_pct"])
        cmax = max(crows, key=lambda r: r["canopy_pct"])
        findings.append({
            "id": "rule-30",
            "text_de": (
                f"Nur {de(canopy['pop_share_canopy_30plus_pct'])} % der Berliner:innen "
                f"({de(canopy['pop_in_lor_canopy_30plus'])} Menschen) leben in einem Planungsraum, "
                f"der die 30-%-Baumkronen-Marke der 3-30-300-Regel für gesundes Stadtgrün erreicht."
            ),
        })
        findings.append({
            "id": "canopy-status-gap",
            "text_de": (
                f"Planungsräume mit hohem Sozialstatus haben im Schnitt "
                f"{de(s[1]['canopy_pct_mean'])} % Baumkronen, solche mit sehr niedrigem Status "
                f"{de(s[4]['canopy_pct_mean'])} % — eine Lücke von "
                f"{de(canopy['canopy_gap_highest_vs_lowest_status'])} Prozentpunkten. "
                f"Ein sauberes Gefälle ist es nicht: am niedrigsten liegt Status "
                f"„{least['class']}“ mit {de(least['canopy_pct_mean'])} %."
            ),
        })
        findings.append({
            "id": "canopy-range",
            "text_de": (
                f"Berlinweit leben die Menschen unter {de(canopy['berlin_canopy_pct_mean'])} % "
                f"Baumkronen. Die Spanne reicht von {de(cmin['canopy_pct'])} % "
                f"({cmin.get('plr_name', '?')}, {cmin.get('bez_name', '?')}) bis {de(cmax['canopy_pct'])} % "
                f"({cmax.get('plr_name', '?')}, {cmax.get('bez_name', '?')})."
            ),
        })
    if heat:
        hrows = [r for r in rows if r.get("pet14h") is not None]
        hot = max(hrows, key=lambda r: r["pet14h"])
        cool = min(hrows, key=lambda r: r["pet14h"])
        findings.append({
            "id": "heat-range",
            "text_de": (
                f"Am modellierten Sommertag reicht die gefühlte Temperatur um 14 Uhr von "
                f"{de(cool['pet14h'])} °C ({cool.get('plr_name', '?')}, {cool.get('bez_name', '?')}) bis "
                f"{de(hot['pet14h'])} °C ({hot.get('plr_name', '?')}, {hot.get('bez_name', '?')}). "
                f"Zwischen den Statusgruppen liegen dagegen nur "
                f"{de(heat['pet14h_gap_lowest_vs_highest_status'])} °C am Tag und "
                f"{de(heat['t2m04h_gap_lowest_vs_highest_status'])} °C in der Nacht."
            ),
        })

    insights = []
    if heat and canopy:
        s = {g["index"]: g for g in by_status}
        least_canopy = min(
            (g for g in by_status if g["canopy_pct_mean"] is not None),
            key=lambda g: g["canopy_pct_mean"],
        )
        insights = [
            {
                "id": "heat-shared",
                "title": "Die Hitze trifft fast alle gleich",
                "text_de": (
                    f"Zwischen den Planungsräumen mit sehr niedrigem und hohem Sozialstatus "
                    f"liegen nachts im Schnitt nur {de(heat['t2m04h_gap_lowest_vs_highest_status'])} °C, "
                    f"am Tag {de(heat['pet14h_gap_lowest_vs_highest_status'])} °C gefühlte Temperatur. "
                    f"Auf LOR-Ebene ist die Hitze weitgehend geteilt."
                ),
            },
            {
                "id": "canopy-divided",
                "title": "Der Schatten ist es nicht",
                "text_de": (
                    f"Wer in einem Planungsraum mit hohem Sozialstatus lebt, hat im Schnitt "
                    f"{de(s[1]['canopy_pct_mean'])} % Baumkronen über sich. Bei sehr niedrigem Status "
                    f"sind es {de(s[4]['canopy_pct_mean'])} % — eine Lücke von "
                    f"{de(canopy['canopy_gap_highest_vs_lowest_status'])} Prozentpunkten. "
                    f"Die Hitze ist geteilt, der Schutz davor nicht."
                ),
            },
            {
                "id": "rule-30",
                "title": "4 von 5 verfehlen die 30-Prozent-Marke",
                "text_de": (
                    f"Nur {de(canopy['pop_share_canopy_30plus_pct'])} % der Berliner:innen "
                    f"({de(canopy['pop_in_lor_canopy_30plus'])} Menschen) leben in einem Planungsraum, "
                    f"der die 30-%-Baumkronen-Marke der 3-30-300-Regel für gesundes Stadtgrün erreicht."
                ),
            },
            {
                "id": "below-average",
                "title": "Die Ungleichheit liegt unter dem Durchschnitt",
                "text_de": (
                    f"Ein sauberes Gefälle ist es nicht: Am wenigsten Baumkronen haben Planungsräume "
                    f"mit Status „{least_canopy['class']}“ ({de(least_canopy['canopy_pct_mean'])} %). "
                    f"Hitze-Ungleichheit entscheidet sich unterhalb der Planungsraum-Mittelwerte — "
                    f"auf Block-Ebene. Genau dort setzt Kapitel 2 an: der Cooling Island Finder."
                ),
            },
        ]
    return {
        "total_lors": len(rows),
        "valid_lors": sum(1 for r in rows if r["mss_valid"]),
        "unassigned_lors": len(unassigned),
        "total_population": total_population,
        "by_status": by_status,
        "heat": heat,
        "canopy": canopy,
        "findings": findings,
        "insights": insights,
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
