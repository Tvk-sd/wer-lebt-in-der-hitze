// Every number shown on this page comes from data/stats.json — never hardcoded.

const STATUS_COLORS = [
  "case",
  ["==", ["get", "mss_status_index"], 1], "#f2f0f7",
  ["==", ["get", "mss_status_index"], 2], "#cbc9e2",
  ["==", ["get", "mss_status_index"], 3], "#9e9ac8",
  ["==", ["get", "mss_status_index"], 4], "#6a51a3",
  "#d9d9d9", // ohne Zuordnung
];

async function init() {
  const stats = await (await fetch("data/stats.json")).json();
  document.getElementById("headline").textContent = stats.headline.text_de;

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
      const ew = (p.ew ?? 0).toLocaleString("de-DE");
      popup
        .setLngLat(e.lngLat)
        .setHTML(
          `<strong>${p.plr_name}</strong> (${p.bez_name})<br>` +
          `Sozialstatus: ${p.mss_status_class}<br>` +
          `Einwohner:innen: ${ew}`
        )
        .addTo(map);
    });
    map.on("mouseleave", "lor-fill", () => {
      if (hoveredId !== null) map.setFeatureState({ source: "lor", id: hoveredId }, { hover: false });
      hoveredId = null;
      map.getCanvas().style.cursor = "";
      popup.remove();
    });
  });
}

init().catch((err) => {
  document.getElementById("headline").textContent = "Daten konnten nicht geladen werden.";
  console.error(err);
});
