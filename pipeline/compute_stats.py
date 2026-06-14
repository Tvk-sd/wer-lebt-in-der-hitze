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

# Source labels attached to every generated finding/insight (PRD: attribution
# travels with the statement, not just in a footer).
SRC = {
    "veg": "Vegetationshöhen 2020, Umweltatlas (SenStadt, DL-DE-Zero-2.0)",
    "mss": "Monitoring Soziale Stadtentwicklung 2025 (SenStadt, Datenstand 12/2024)",
    "klima": "Klimamodell Berlin 2022, Klimaanalysekarten (SenStadt/GEO-NET, FITNAH 3D)",
    "lor": "LOR Planungsräume 01.01.2021 (Geoportal Berlin)",
    "rule": "3-30-300-Regel nach Konijnendijk (2022)",
}


def de(value):
    """German number formatting: 6.34 -> '6,34', 755469 -> '755.469'."""
    if isinstance(value, int):
        return f"{value:,}".replace(",", ".")
    return f"{value:,}".translate(str.maketrans(",.", ".,"))


PET_HOT = 38.0  # threshold for "hottest LORs" in the inversion finding


def pearson(rows, key_x, key_y):
    """Pearson correlation over LORs where both values exist (unweighted)."""
    pairs = [(r[key_x], r[key_y]) for r in rows
             if r.get(key_x) is not None and r.get(key_y) is not None]
    n = len(pairs)
    mx = sum(x for x, _ in pairs) / n
    my = sum(y for _, y in pairs) / n
    cov = sum((x - mx) * (y - my) for x, y in pairs)
    sx = sum((x - mx) ** 2 for x, _ in pairs) ** 0.5
    sy = sum((y - my) ** 2 for _, y in pairs) ** 0.5
    return round(cov / (sx * sy), 2)


def pop_share_above(rows, key, threshold):
    """Share of a group's population living in LORs at/above a threshold."""
    total = sum(r["ew"] or 0 for r in rows)
    above = sum(r["ew"] or 0 for r in rows
                if r.get(key) is not None and r[key] >= threshold)
    return round(100 * above / total, 1) if total else None


def pop_weighted_mean(rows, key):
    """Population-weighted mean of `key` over rows that have a value.
    Weighted by people, not area — the study asks who LIVES in the heat."""
    pairs = [(r["ew"] or 0, r[key]) for r in rows if r.get(key) is not None]
    total = sum(ew for ew, _ in pairs)
    if total == 0:
        return None
    return round(sum(ew * v for ew, v in pairs) / total, 2)


def build_methodology(rows):
    """Methodology chapter content — generated, so its numbers stay true."""
    n = len(rows)
    unassigned = sum(1 for r in rows if r["mss_status_index"] is None)
    return [
        {
            "title": "Räumliche Einheit",
            "text_de": (
                f"Alle Aussagen beziehen sich auf Berlins {n} LOR-Planungsräume "
                f"(Stand 01.01.2021). {unassigned} davon tragen keinen Sozialstatus "
                f"(unter 300 Einwohner:innen oder statistischer Ausreißer); sie bleiben "
                f"im Datensatz, werden aber bei Statusvergleichen ausgeschlossen."
            ),
            "sources": [SRC["lor"], SRC["mss"]],
        },
        {
            "title": "Sozialstatus",
            "text_de": (
                "Sozialstatus ist der Statusindex des Monitorings Soziale Stadtentwicklung "
                "(vier Klassen: hoch bis sehr niedrig) — ein zusammengesetzter Index aus "
                "Arbeitslosigkeit, Transferbezug und Kinderarmut, kein Einkommensmaß."
            ),
            "sources": [SRC["mss"]],
        },
        {
            "title": "Hitze",
            "text_de": (
                "Die Hitzewerte sind keine Messwerte, sondern eine FITNAH-3D-Simulation "
                "(10×10 m) eines durchschnittlichen wolkenlosen, windschwachen Sommertags "
                "auf Basis der Stadtstruktur 2022. PET 14 Uhr beschreibt die gefühlte "
                "Hitzebelastung am Tag, die Lufttemperatur um 4 Uhr die nächtliche "
                "Wärmeinsel. Blockwerte wurden flächengewichtet auf Planungsräume gemittelt."
            ),
            "sources": [SRC["klima"]],
        },
        {
            "title": "Baumkronen",
            "text_de": (
                "Baumkronenanteil = Vegetation ab 4 m Höhe im 1×1m-Laserscan-Raster von 2020, "
                "als Anteil an der gesamten Planungsraum-Fläche einschließlich Wasser- und "
                "versiegelter Flächen. Erfasst sind öffentliche und private Bäume."
            ),
            "sources": [SRC["veg"]],
        },
        {
            "title": "Gewichtung",
            "text_de": (
                "Alle veröffentlichten Mittelwerte sind bevölkerungsgewichtet — gefragt wird, "
                "unter welchen Bedingungen Menschen leben, nicht wie heiß Flächen sind."
            ),
            "sources": [SRC["mss"]],
        },
        {
            "title": "Grenzen",
            "text_de": (
                "Die Datenstände unterscheiden sich (Baumkronen 2020, Klimamodell 2022, "
                "Sozialdaten 12/2024). Planungsraum-Mittelwerte glätten Extremwerte einzelner "
                "Blöcke — Unterschiede innerhalb der Räume sind unsichtbar. Korrelation ist "
                "keine Kausalität; der starke Zusammenhang von Baumkronen und Tageshitze ist "
                "physikalisch plausibel, hier aber rein statistisch gezeigt."
            ),
            "sources": [SRC["veg"], SRC["klima"], SRC["mss"]],
        },
    ]


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
            "sources": [SRC["veg"], SRC["mss"], SRC["rule"]],
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
            "sources": [SRC["veg"], SRC["mss"]],
        })
        findings.append({
            "id": "canopy-range",
            "text_de": (
                f"Berlinweit leben die Menschen unter {de(canopy['berlin_canopy_pct_mean'])} % "
                f"Baumkronen. Die Spanne reicht von {de(cmin['canopy_pct'])} % "
                f"({cmin.get('plr_name', '?')}, {cmin.get('bez_name', '?')}) bis {de(cmax['canopy_pct'])} % "
                f"({cmax.get('plr_name', '?')}, {cmax.get('bez_name', '?')})."
            ),
            "sources": [SRC["veg"], SRC["lor"]],
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
            "sources": [SRC["klima"], SRC["mss"]],
        })

    def extreme(key, pick):
        have = [r for r in rows if r.get(key) is not None]
        r = pick(have, key=lambda r: r[key])
        return {
            "plr_id": r["plr_id"],
            "plr_name": r.get("plr_name"),
            "bez_name": r.get("bez_name"),
            "value": r[key],
        }

    extremes = None
    if has_heat and has_canopy:
        extremes = {
            "pet_max": extreme("pet14h", max),
            "pet_min": extreme("pet14h", min),
            "night_max": extreme("t2m04h", max),
            "night_min": extreme("t2m04h", min),
            "canopy_max": extreme("canopy_pct", max),
            "canopy_min": extreme("canopy_pct", min),
        }

    correlations = None
    lead = None
    if heat and canopy:
        correlations = {
            "canopy_pet14h": pearson(rows, "canopy_pct", "pet14h"),
            "canopy_t2m04h": pearson(rows, "canopy_pct", "t2m04h"),
        }
        findings.append({
            "id": "canopy-cooling",
            "text_de": (
                f"Baumkronen kühlen den Tag: Über alle {len(rows)} Planungsräume korreliert "
                f"der Baumkronenanteil stark negativ mit der gefühlten Temperatur um 14 Uhr "
                f"(r = {de(correlations['canopy_pet14h'])}). Nachts ist der Zusammenhang schwach "
                f"(r = {de(correlations['canopy_t2m04h'])}) — die nächtliche Wärmeinsel folgt "
                f"der Bebauung, nicht dem Grün."
            ),
            "sources": [SRC["veg"], SRC["klima"], SRC["lor"]],
        })
        hot_share = {
            idx: pop_share_above(
                [r for r in rows if r["mss_status_index"] == idx], "pet14h", PET_HOT
            )
            for idx in STATUS_CLASSES
        }
        findings.append({
            "id": "heat-inversion",
            "text_de": (
                f"In den heißesten Planungsräumen (PET ≥ {de(PET_HOT)} °C) wohnen vor allem "
                f"Menschen mit hohem Sozialstatus ({de(hot_share[1])} % dieser Gruppe) — und "
                f"praktisch niemand mit sehr niedrigem Status ({de(hot_share[4])} %). "
                f"Ein „Arm wohnt heiß“ gibt es auf Planungsraum-Ebene nicht."
            ),
            "sources": [SRC["klima"], SRC["mss"]],
        })
        # Lead headline — chosen by the author (issue 04, 2026-06-11):
        # the 3-30-300 failure leads; "1 von N" derived from the computed share.
        one_in_n = round(100 / canopy["pop_share_canopy_30plus_pct"])
        lead = {
            "text_de": f"Nur 1 von {one_in_n} Berliner:innen lebt unter genug Baumkronen.",
            "sub_de": (
                f"{de(round(100 - canopy['pop_share_canopy_30plus_pct'], 1))} % der Stadt "
                f"wohnen in Planungsräumen unterhalb der 30-%-Baumkronen-Marke der "
                f"3-30-300-Regel für gesundes Stadtgrün."
            ),
            "sources": [SRC["veg"], SRC["mss"], SRC["rule"]],
        }

    # Insights interpret the findings; they reference them ("Befund N") and
    # deliberately repeat none of their numbers (CONTEXT.md: Befund vs. Einordnung).
    insights = []
    if heat and canopy:
        insights = [
            {
                "id": "heat-shared-canopy-not",
                "title": "Die Hitze ist geteilt — der Schutz nicht",
                "text_de": (
                    "Bei der Temperatur unterscheiden sich die Statusgruppen kaum (Befund 4), "
                    "beim Baumkronendach dagegen deutlich (Befund 2). Die Belastung trifft fast "
                    "alle ähnlich — die Abschirmung folgt dem Sozialstatus."
                ),
                "sources": [SRC["klima"], SRC["veg"], SRC["mss"]],
            },
            {
                "id": "canopy-lever",
                "title": "Baumkronen sind der Hebel",
                "text_de": (
                    "Temperatur lässt sich nicht umverteilen — Baumkronen schon. Das Kronendach "
                    "ist die Stellgröße, die eine Stadt tatsächlich verändern kann, und genau "
                    "sie ist ungleich verteilt (Befunde 1 und 2)."
                ),
                "sources": [SRC["veg"], SRC["mss"], SRC["rule"]],
            },
            {
                "id": "canopy-day-only",
                "title": "Schatten wirkt am Tag, nicht in der Nacht",
                "text_de": (
                    "Wo Kronen sind, ist es tagsüber deutlich kühler — der Zusammenhang ist "
                    "stark (Befund 5). Nachts verschwindet er fast: Die Wärmeinsel folgt dann "
                    "der Bebauung, nicht dem Grün. Bäume sind ein Schutz gegen die Tageshitze, "
                    "kein Allheilmittel. Dass Schatten Strahlung bremst, ist physikalisch "
                    "plausibel; die Daten zeigen den Zusammenhang, beweisen aber keine Ursache."
                ),
                "sources": [SRC["veg"], SRC["klima"]],
            },
            {
                "id": "below-average",
                "title": "Die Ungleichheit liegt unter dem Durchschnitt",
                "text_de": (
                    "Weder Hitze noch Grün bilden ein sauberes Gefälle über die Statusgruppen "
                    "(Befunde 2 und 4). Die eigentlichen Unterschiede liegen unterhalb der "
                    "Planungsraum-Mittelwerte, auf Block-Ebene. Genau dort setzt Kapitel 2 an: "
                    "der Cooling Island Finder."
                ),
                "sources": [SRC["veg"], SRC["klima"], SRC["mss"]],
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
        "correlations": correlations,
        "extremes": extremes,
        "lead": lead,
        "findings": findings,
        "insights": insights,
        "methodology": build_methodology(rows) if (heat and canopy) else None,
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
