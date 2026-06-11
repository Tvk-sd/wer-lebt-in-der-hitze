// Every number shown on this page comes from data/stats.json — never hardcoded.

const STATUS_COLORS = [
  "case",
  ["==", ["get", "mss_status_index"], 1], "#f2f0f7",
  ["==", ["get", "mss_status_index"], 2], "#cbc9e2",
  ["==", ["get", "mss_status_index"], 3], "#9e9ac8",
  ["==", ["get", "mss_status_index"], 4], "#6a51a3",
  "#d9d9d9", // ohne Zuordnung
];

const LAYER_PAINT = {
  status: STATUS_COLORS,
  pet: [
    "interpolate", ["linear"], ["coalesce", ["get", "pet14h"], 27],
    27, "#ffffb2", 34, "#fd8d3c", 40, "#b10026",
  ],
  night: [
    "interpolate", ["linear"], ["coalesce", ["get", "t2m04h"], 15.5],
    15.5, "#ffffcc", 17.5, "#fe9929", 19.5, "#993404",
  ],
  canopy: [
    "interpolate", ["linear"], ["coalesce", ["get", "canopy_pct"], 0],
    0, "#f7fcf5", 30, "#74c476", 75, "#00441b",
  ],
};

function fmt(n) {
  return n.toLocaleString("de-DE");
}

function renderHeatChapter(stats) {
  const h = stats.heat;
  if (!h) return;
  document.getElementById("heat-text").textContent =
    `Tagsüber liegt die gefühlte Temperatur (PET) im Berliner Schnitt bei ${fmt(h.berlin_pet14h_mean)} °C, ` +
    `nachts kühlt die Stadt im Mittel auf ${fmt(h.berlin_t2m04h_mean)} °C ab. Zwischen den Planungsräumen ` +
    `mit sehr niedrigem und hohem Sozialstatus liegt dabei eine Lücke von ` +
    `${fmt(h.pet14h_gap_lowest_vs_highest_status)} °C am Tag und ${fmt(h.t2m04h_gap_lowest_vs_highest_status)} °C in der Nacht.`;
  document.getElementById("heat-note").textContent = h.note;

  const chart = document.getElementById("heat-chart");
  chart.innerHTML = "";
  const values = stats.by_status.map((g) => g.t2m04h_mean);
  const min = Math.min(...values) - 0.3;
  const max = Math.max(...values);
  for (const g of stats.by_status) {
    const rowEl = document.createElement("div");
    rowEl.className = "bar-row";
    const pct = ((g.t2m04h_mean - min) / (max - min)) * 100;
    rowEl.innerHTML =
      `<span class="bar-label">Status ${g.class}</span>` +
      `<span class="bar" style="width:${pct}%"></span>` +
      `<span class="bar-value">${fmt(g.t2m04h_mean)} °C</span>`;
    chart.appendChild(rowEl);
  }
}

function renderCanopyChapter(stats) {
  const c = stats.canopy;
  if (!c) return;
  document.getElementById("canopy-text").textContent =
    `Im Berliner Schnitt leben die Menschen unter ${fmt(c.berlin_canopy_pct_mean)} % Baumkronen. ` +
    `In Planungsräumen mit hohem Sozialstatus sind es deutlich mehr als in den übrigen — die Lücke ` +
    `zwischen hohem und sehr niedrigem Status beträgt ${fmt(c.canopy_gap_highest_vs_lowest_status)} Prozentpunkte. ` +
    `Die 30-%-Marke der 3-30-300-Regel erreichen nur Planungsräume, in denen ` +
    `${fmt(c.pop_in_lor_canopy_30plus)} Berliner:innen leben (${fmt(c.pop_share_canopy_30plus_pct)} %).`;
  document.getElementById("canopy-note").textContent = c.note;

  const chart = document.getElementById("canopy-chart");
  chart.innerHTML = "";
  const max = Math.max(...stats.by_status.map((g) => g.canopy_pct_mean));
  for (const g of stats.by_status) {
    const rowEl = document.createElement("div");
    rowEl.className = "bar-row";
    rowEl.innerHTML =
      `<span class="bar-label">Status ${g.class}</span>` +
      `<span class="bar" style="width:${(g.canopy_pct_mean / max) * 100}%"></span>` +
      `<span class="bar-value">${fmt(g.canopy_pct_mean)} %</span>`;
    chart.appendChild(rowEl);
  }
}

function renderInsights(stats) {
  const grid = document.getElementById("insights");
  grid.innerHTML = "";
  for (const ins of stats.insights ?? []) {
    const card = document.createElement("article");
    card.className = "insight-card";
    const h3 = document.createElement("h3");
    h3.textContent = ins.title;
    const p = document.createElement("p");
    p.textContent = ins.text_de;
    card.append(h3, p);
    grid.appendChild(card);
  }
}

function wireLayerToggle(map) {
  const buttons = document.querySelectorAll(".layer-toggle button");
  buttons.forEach((btn) => {
    btn.addEventListener("click", () => {
      buttons.forEach((b) => b.classList.toggle("active", b === btn));
      const layer = btn.dataset.layer;
      map.setPaintProperty("lor-fill", "fill-color", LAYER_PAINT[layer]);
      for (const key of ["status", "pet", "night", "canopy"]) {
        document.getElementById(`legend-${key}`).classList.toggle("hidden", key !== layer);
      }
    });
  });
}

async function init() {
  const stats = await (await fetch("data/stats.json")).json();
  document.getElementById("headline").textContent = stats.headline.text_de;
  renderHeatChapter(stats);
  renderCanopyChapter(stats);
  renderInsights(stats);

  const map = new maplibregl.Map({
    container: "map",
    style: { version: 8, sources: {}, layers: [
      { id: "bg", type: "background", paint: { "background-color": "#fbfaf8" } },
    ] },
    center: [13.4, 52.5],
    zoom: 9.3,
    attributionControl: { customAttribution: "Daten: Geoportal Berlin, MSS 2025" },
  });
  map.addControl(new maplibregl.NavigationControl(), "top-right");

  map.on("load", async () => {
    map.addSource("lor", {
      type: "geojson",
      data: "data/lor_dataset.geojson",
      promoteId: "plr_id",
    });
    map.addLayer({
      id: "lor-fill",
      type: "fill",
      source: "lor",
      paint: {
        "fill-color": STATUS_COLORS,
        "fill-opacity": ["case", ["boolean", ["feature-state", "hover"], false], 1, 0.85],
      },
    });
    map.addLayer({
      id: "lor-line",
      type: "line",
      source: "lor",
      paint: { "line-color": "#ffffff", "line-width": 0.5 },
    });

    const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false });
    let hoveredId = null;

    map.on("mousemove", "lor-fill", (e) => {
      const f = e.features[0];
      if (hoveredId !== null) map.setFeatureState({ source: "lor", id: hoveredId }, { hover: false });
      hoveredId = f.id;
      map.setFeatureState({ source: "lor", id: hoveredId }, { hover: true });
      map.getCanvas().style.cursor = "pointer";
      const p = f.properties;
      const heat = p.pet14h != null
        ? `<br>PET 14 Uhr: ${fmt(p.pet14h)} °C · Nachts: ${fmt(p.t2m04h)} °C`
        : "";
      const canopy = p.canopy_pct != null
        ? `<br>Baumkronen: ${fmt(p.canopy_pct)} %`
        : "";
      popup
        .setLngLat(e.lngLat)
        .setHTML(
          `<strong>${p.plr_name}</strong> (${p.bez_name})<br>` +
          `Sozialstatus: ${p.mss_status_class}<br>` +
          `Einwohner:innen: ${fmt(p.ew ?? 0)}` + heat + canopy
        )
        .addTo(map);
    });
    map.on("mouseleave", "lor-fill", () => {
      if (hoveredId !== null) map.setFeatureState({ source: "lor", id: hoveredId }, { hover: false });
      hoveredId = null;
      map.getCanvas().style.cursor = "";
      popup.remove();
    });

    wireLayerToggle(map);
  });
}

init().catch((err) => {
  document.getElementById("headline").textContent = "Daten konnten nicht geladen werden.";
  console.error(err);
});
