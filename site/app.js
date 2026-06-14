// "Wer lebt in der Hitze?" — scrollytelling driver.
// Contract: every number on this page comes from data/stats.json or the
// dataset — narrative templates below inject values, never contain them.

const REDUCED = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function fmt(n) {
  return n.toLocaleString("de-DE");
}

/* ——— map paint per layer ——— */

const LAYER_PAINT = {
  status: [
    "case",
    ["==", ["get", "mss_status_index"], 1], "#eef0ef",
    ["==", ["get", "mss_status_index"], 2], "#b9c4cf",
    ["==", ["get", "mss_status_index"], 3], "#7d92ab",
    ["==", ["get", "mss_status_index"], 4], "#3c5475",
    "#d9d2c2",
  ],
  pet: [
    "interpolate", ["linear"], ["coalesce", ["get", "pet14h"], 27],
    27, "#f7e8b4", 34, "#e4572e", 40, "#8c1d18",
  ],
  night: [
    "interpolate", ["linear"], ["coalesce", ["get", "t2m04h"], 15.5],
    15.5, "#f4ecd7", 17.5, "#d98c3f", 19.5, "#5e2a18",
  ],
  canopy: [
    "interpolate", ["linear"], ["coalesce", ["get", "canopy_pct"], 0],
    0, "#f1ead3", 30, "#6fa07c", 75, "#1c4734",
  ],
  rule30: [
    "case",
    [">=", ["coalesce", ["get", "canopy_pct"], 0], 30], "#2f6b4f",
    "#e8b49a",
  ],
};

const LEGENDS = {
  status: { title: "Sozialstatus (MSS 2025)", items: [["#eef0ef", "hoch"], ["#b9c4cf", "mittel"], ["#7d92ab", "niedrig"], ["#3c5475", "sehr niedrig"], ["#d9d2c2", "ohne Zuordnung"]] },
  pet: { title: "Gefühlte Temperatur 14 Uhr (PET)", items: [["#f7e8b4", "27 °C"], ["#e4572e", "34 °C"], ["#8c1d18", "40 °C"]] },
  night: { title: "Lufttemperatur 4 Uhr", items: [["#f4ecd7", "15,5 °C"], ["#d98c3f", "17,5 °C"], ["#5e2a18", "19,5 °C"]] },
  canopy: { title: "Baumkronenanteil (ab 4 m)", items: [["#f1ead3", "0 %"], ["#6fa07c", "30 %"], ["#1c4734", "75 %"]] },
  rule30: { title: "Die 30-%-Marke (3-30-300)", items: [["#2f6b4f", "erreicht"], ["#e8b49a", "verfehlt"]] },
};

/* ——— narrative steps, built from stats ——— */

function buildSteps(stats, byId) {
  const ex = stats.extremes;
  const c = stats.canopy;
  const h = stats.heat;
  const cls = Object.fromEntries(stats.by_status.map((g) => [g.index, g]));
  const place = (e) => `${e.plr_name} (${e.bez_name})`;

  return [
    {
      layer: "pet", target: "city", kicker: "Kapitel 1 · Ein Sommertag im Modell", tone: "",
      title: "So heiß ist Berlin gebaut",
      html: `<p>Diese Karte zeigt keinen Messtag, sondern Berlins Struktur: eine Simulation
        der gefühlten Temperatur an einem durchschnittlichen wolkenlosen, windschwachen
        Sommertag, 14 Uhr. Dunkel heißt heiß — an <strong>jedem</strong> solchen Tag.</p>`,
      sources: stats.methodology?.[2]?.sources,
    },
    {
      layer: "pet", target: ex.pet_max.plr_id, kicker: "Kapitel 1 · Ein Sommertag im Modell", tone: "",
      title: `Am heißesten: ${ex.pet_max.plr_name}`,
      html: `<p class="step-big">${fmt(ex.pet_max.value)} °C</p>
        <p>gefühlte Temperatur erreicht ${place(ex.pet_max)} um 14 Uhr —
        der heißeste Planungsraum der Stadt.</p>`,
      sources: stats.findings.find((f) => f.id === "heat-range")?.sources,
    },
    {
      layer: "pet", target: ex.pet_min.plr_id, kicker: "Kapitel 1 · Ein Sommertag im Modell", tone: "",
      title: `Am kühlsten: ${ex.pet_min.plr_name}`,
      html: `<p class="step-big green">${fmt(ex.pet_min.value)} °C</p>
        <p>misst das Modell in ${place(ex.pet_min)} — gut
        ${fmt(Math.round(ex.pet_max.value - ex.pet_min.value))} Grad weniger, am selben Tag,
        in derselben Stadt. Was macht den Unterschied?</p>`,
      sources: stats.findings.find((f) => f.id === "heat-range")?.sources,
    },
    {
      layer: "canopy", target: "city", kicker: "Kapitel 2 · Bäume kühlen", tone: "green",
      title: "Die Antwort steht am Straßenrand",
      html: `<p>Gleiche Karte, neue Ebene: der Baumkronenanteil. Wo es grün ist, war es eben
        hell — über alle ${fmt(stats.total_lors)} Planungsräume korreliert das Kronendach
        stark negativ mit der Tageshitze (r&nbsp;=&nbsp;${fmt(stats.correlations.canopy_pet14h)}).
        Nachts ist der Zusammenhang schwach (r&nbsp;=&nbsp;${fmt(stats.correlations.canopy_t2m04h)}):
        Die nächtliche Wärmeinsel folgt der Bebauung, nicht dem Grün.</p>`,
      sources: stats.findings.find((f) => f.id === "canopy-cooling")?.sources,
    },
    {
      layer: "canopy", target: ex.canopy_max.plr_id, kicker: "Kapitel 2 · Bäume kühlen", tone: "green",
      title: `${ex.canopy_max.plr_name}: Leben unterm Kronendach`,
      html: `<p class="step-big green">${fmt(ex.canopy_max.value)} %</p>
        <p>von ${place(ex.canopy_max)} liegen unter Baumkronen — und genau hier zeigt die
        Tageskarte ihren kühlsten Wert. Grünster und kühlster Planungsraum: derselbe Ort.</p>
        <p>Das Schlusslicht beim Grün ist ${place(ex.canopy_min)} mit
        ${fmt(ex.canopy_min.value)} % — mit ${fmt(byId[ex.canopy_min.plr_id].pet14h)} °C
        sehr heiß, aber nicht der Rekord. Den hält ${ex.pet_max.plr_name} (Kapitel 1) —
        mit ${fmt(byId[ex.pet_max.plr_id].canopy_pct)} % Kronen ebenfalls fast baumlos.</p>`,
      sources: stats.findings.find((f) => f.id === "canopy-range")?.sources,
    },
    {
      layer: "status", target: "city", kicker: "Kapitel 3 · Wer hat die Kronen?", tone: "slate",
      title: "Die soziale Landkarte",
      html: `<p>Das Monitoring Soziale Stadtentwicklung teilt die Planungsräume in vier
        Statusklassen — von hoch bis sehr niedrig, zusammengesetzt aus Arbeitslosigkeit,
        Transferbezug und Kinderarmut. ${fmt(stats.headline.disadvantaged_population)}
        Berliner:innen (${fmt(stats.headline.disadvantaged_pop_share_pct)} %) leben in Räumen
        mit niedrigem oder sehr niedrigem Status.</p>`,
      sources: stats.methodology?.[1]?.sources,
    },
    {
      layer: "canopy", target: "city", kicker: "Kapitel 3 · Wer hat die Kronen?", tone: "slate",
      title: "Der Schatten folgt dem Status",
      html: `<p>Bei der Hitze trennen die Statusgruppen kaum etwas — am Tag im Schnitt nur
        ${fmt(h.pet14h_gap_lowest_vs_highest_status)} °C. Beim Schatten dagegen klafft eine
        Lücke: Wer in einem Planungsraum mit hohem Sozialstatus lebt, hat im Schnitt
        <strong>${fmt(cls[1].canopy_pct_mean)} %</strong> Baumkronen über sich, bei sehr
        niedrigem Status <strong>${fmt(cls[4].canopy_pct_mean)} %</strong>. Kein sauberes
        Gefälle von arm zu reich, aber die Richtung ist klar.</p>
        <p><strong>Die Hitze ist geteilt — der Schutz davor nicht.</strong></p>
        <div class="bars bars-green" role="img" aria-label="Baumkronenanteil nach Sozialstatus"></div>`,
      chart: { metric: "canopy_pct_mean", unit: " %", green: true },
      sources: stats.findings.find((f) => f.id === "canopy-status-gap")?.sources,
    },
    {
      layer: "rule30", target: "city", kicker: "Kapitel 3 · Wer hat die Kronen?", tone: "green",
      title: "Die 30-Prozent-Marke",
      html: `<p class="step-big">${fmt(c.pop_share_canopy_30plus_pct)} %</p>
        <p>der Berliner:innen — ${fmt(c.pop_in_lor_canopy_30plus)} Menschen — leben in einem
        Planungsraum, der die 30-%-Baumkronen-Marke der 3-30-300-Regel für gesundes
        Stadtgrün erreicht. Der Rest der Karte: verfehlt.</p>`,
      sources: stats.lead?.sources,
    },
  ];
}

/* ——— rendering helpers ——— */

function sourcesLine(item) {
  if (!item?.sources?.length) return null;
  const small = document.createElement("small");
  small.className = "source-line";
  small.textContent = "Quellen: " + item.sources.join(" · ");
  return small;
}

function buildBars(container, stats, { metric, unit, green }) {
  const groups = stats.by_status;
  const values = groups.map((g) => g[metric]);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const floor = metric.includes("t2m") ? min - 0.3 : 0;
  for (const g of groups) {
    const row = document.createElement("div");
    row.className = "bar-row";
    const pct = ((g[metric] - floor) / (max - floor)) * 100;
    row.innerHTML =
      `<span class="bar-label">Status ${g.class}</span>` +
      `<span class="bar" style="width:${pct}%"></span>` +
      `<span class="bar-value">${fmt(g[metric])}${unit}</span>`;
    container.appendChild(row);
  }
}

function renderSteps(stats, propsById) {
  const wrap = document.getElementById("steps");
  const steps = buildSteps(stats, propsById);
  steps.forEach((spec, i) => {
    const step = document.createElement("div");
    step.className = "step";
    step.dataset.index = i;
    const card = document.createElement("article");
    card.className = "step-card";
    card.innerHTML =
      `<p class="step-kicker ${spec.tone}">${spec.kicker}</p>` +
      `<h2>${spec.title}</h2>` + spec.html;
    if (spec.chart) {
      buildBars(card.querySelector(".bars"), stats, spec.chart);
    }
    const src = sourcesLine(spec);
    if (src) card.appendChild(src);
    step.appendChild(card);
    wrap.appendChild(step);
  });
  return steps;
}

function renderList(stats) {
  const list = document.getElementById("findings");
  for (const f of stats.findings ?? []) {
    const li = document.createElement("li");
    const p = document.createElement("p");
    p.textContent = f.text_de;
    li.appendChild(p);
    const src = sourcesLine(f);
    if (src) li.appendChild(src);
    list.appendChild(li);
  }
  const grid = document.getElementById("insights");
  for (const ins of stats.insights ?? []) {
    const card = document.createElement("article");
    card.className = "insight-card";
    const h3 = document.createElement("h3");
    h3.textContent = ins.title;
    const p = document.createElement("p");
    p.textContent = ins.text_de;
    card.append(h3, p);
    const src = sourcesLine(ins);
    if (src) card.appendChild(src);
    grid.appendChild(card);
  }
  if (stats.methodology) {
    document.getElementById("methodology-chapter").hidden = false;
    const wrap = document.getElementById("methodology");
    for (const item of stats.methodology) {
      const block = document.createElement("div");
      block.className = "method-item";
      const h3 = document.createElement("h3");
      h3.textContent = item.title;
      const p = document.createElement("p");
      p.textContent = item.text_de;
      block.append(h3, p);
      const src = sourcesLine(item);
      if (src) block.appendChild(src);
      wrap.appendChild(block);
    }
  }
}

function setLegend(layer) {
  const spec = LEGENDS[layer];
  const el = document.getElementById("legend");
  el.innerHTML = `<strong>${spec.title}</strong>` + spec.items
    .map(([color, label]) => `<span><i style="background:${color}"></i>${label}</span>`)
    .join("");
}

/* ——— geometry helpers ——— */

function bboxOfGeometry(geometry) {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  const walk = (coords) => {
    if (typeof coords[0] === "number") {
      minX = Math.min(minX, coords[0]); maxX = Math.max(maxX, coords[0]);
      minY = Math.min(minY, coords[1]); maxY = Math.max(maxY, coords[1]);
    } else coords.forEach(walk);
  };
  walk(geometry.coordinates);
  return [[minX, minY], [maxX, maxY]];
}

/* ——— init ——— */

async function init() {
  const [stats, dataset] = await Promise.all([
    fetch("data/stats.json").then((r) => r.json()),
    fetch("data/lor_dataset.geojson").then((r) => r.json()),
  ]);

  if (stats.lead) {
    document.getElementById("headline").textContent = stats.lead.text_de;
    document.getElementById("headline-sub").textContent = stats.lead.sub_de;
  } else {
    document.getElementById("headline").textContent = stats.headline.text_de;
  }

  renderList(stats);

  const bboxes = {};
  const propsById = {};
  let cityBounds = null;
  for (const f of dataset.features) {
    const b = bboxOfGeometry(f.geometry);
    bboxes[f.properties.plr_id] = b;
    propsById[f.properties.plr_id] = f.properties;
    if (!cityBounds) cityBounds = [[...b[0]], [...b[1]]];
    else {
      cityBounds[0][0] = Math.min(cityBounds[0][0], b[0][0]);
      cityBounds[0][1] = Math.min(cityBounds[0][1], b[0][1]);
      cityBounds[1][0] = Math.max(cityBounds[1][0], b[1][0]);
      cityBounds[1][1] = Math.max(cityBounds[1][1], b[1][1]);
    }
  }

  const steps = renderSteps(stats, propsById);

  // Berlin is the fixed frame: pan fenced to the city, zoom-out capped at the
  // full-city fit. Plain scrolling must always scroll the PAGE — zooming is a
  // deliberate act (Ctrl/⌘+Scroll, two fingers, or the +/− buttons).
  const fence = [
    [cityBounds[0][0] - 0.08, cityBounds[0][1] - 0.05],
    [cityBounds[1][0] + 0.08, cityBounds[1][1] + 0.05],
  ];
  const map = new maplibregl.Map({
    container: "map",
    style: {
      version: 8,
      sources: {},
      layers: [{ id: "bg", type: "background", paint: { "background-color": "#eee4cd" } }],
    },
    bounds: cityBounds,
    fitBoundsOptions: { padding: 30 },
    maxBounds: fence,
    cooperativeGestures: true,
    locale: {
      "CooperativeGesturesHandler.WindowsHelpText": "Strg + Scrollen zum Zoomen der Karte",
      "CooperativeGesturesHandler.MacHelpText": "⌘ + Scrollen zum Zoomen der Karte",
      "CooperativeGesturesHandler.MobileHelpText": "Karte mit zwei Fingern bewegen",
    },
    attributionControl: { customAttribution: "Daten: Geoportal Berlin · MSS 2025 · Klimamodell 2022 · Vegetationshöhen 2020" },
  });
  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
  map.once("load", () => map.setMinZoom(Math.max(map.getZoom() - 0.2, 7)));

  map.on("load", () => {
    map.addSource("lor", { type: "geojson", data: dataset, promoteId: "plr_id" });
    map.addLayer({
      id: "lor-fill", type: "fill", source: "lor",
      paint: {
        "fill-color": LAYER_PAINT.pet,
        "fill-color-transition": { duration: REDUCED ? 0 : 600 },
        "fill-opacity": ["case", ["boolean", ["feature-state", "hover"], false], 1, 0.92],
      },
    });
    map.addLayer({
      id: "lor-line", type: "line", source: "lor",
      paint: { "line-color": "#f6efe1", "line-width": 0.4 },
    });
    map.addLayer({
      id: "lor-highlight", type: "line", source: "lor",
      filter: ["==", ["get", "plr_id"], ""],
      paint: { "line-color": "#231a10", "line-width": 2.4 },
    });

    setLegend("pet");
    syncToggle("pet");

    /* LOR details: hover preview on desktop, persistent popup on click/tap */
    const lorHTML = (p) =>
      `<strong>${p.plr_name}</strong> (${p.bez_name})<br>` +
      `Sozialstatus: ${p.mss_status_class}<br>` +
      `Einwohner:innen: ${fmt(p.ew ?? 0)}<br>` +
      `PET 14 Uhr: ${fmt(p.pet14h)} °C · Nachts: ${fmt(p.t2m04h)} °C<br>` +
      `Baumkronen: ${fmt(p.canopy_pct)} %`;

    const hoverPopup = new maplibregl.Popup({ closeButton: false, closeOnClick: false });
    const clickPopup = new maplibregl.Popup({ closeButton: true, closeOnClick: true });
    let hoveredId = null;

    map.on("mousemove", "lor-fill", (e) => {
      const f = e.features[0];
      if (hoveredId !== null) map.setFeatureState({ source: "lor", id: hoveredId }, { hover: false });
      hoveredId = f.id;
      map.setFeatureState({ source: "lor", id: hoveredId }, { hover: true });
      map.getCanvas().style.cursor = "pointer";
      if (!clickPopup.isOpen()) {
        hoverPopup.setLngLat(e.lngLat).setHTML(lorHTML(f.properties)).addTo(map);
      }
    });
    map.on("mouseleave", "lor-fill", () => {
      if (hoveredId !== null) map.setFeatureState({ source: "lor", id: hoveredId }, { hover: false });
      hoveredId = null;
      map.getCanvas().style.cursor = "";
      hoverPopup.remove();
    });
    map.on("click", "lor-fill", (e) => {
      hoverPopup.remove();
      clickPopup.setLngLat(e.lngLat).setHTML(lorHTML(e.features[0].properties)).addTo(map);
    });

    /* scroll driver */
    const stepEls = document.querySelectorAll(".step");
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue;
          const spec = steps[Number(entry.target.dataset.index)];
          stepEls.forEach((el) => el.classList.toggle("is-active", el === entry.target));
          applyState(spec);
        }
      },
      { threshold: 0.55 }
    );
    stepEls.forEach((el) => observer.observe(el));
  });

  function applyState(spec) {
    map.setPaintProperty("lor-fill", "fill-color", LAYER_PAINT[spec.layer]);
    setLegend(spec.layer);
    syncToggle(spec.layer);
    if (spec.target === "city") {
      map.setFilter("lor-highlight", ["==", ["get", "plr_id"], ""]);
      map.fitBounds(cityBounds, { padding: 30, duration: REDUCED ? 0 : 1400 });
    } else if (bboxes[spec.target]) {
      map.setFilter("lor-highlight", ["==", ["get", "plr_id"], spec.target]);
      map.fitBounds(bboxes[spec.target], { padding: 140, maxZoom: 12.5, duration: REDUCED ? 0 : 1800 });
    }
  }

  function syncToggle(layer) {
    document.querySelectorAll(".layer-toggle button").forEach((b) =>
      b.classList.toggle("active", b.dataset.layer === layer)
    );
  }

  document.querySelectorAll(".layer-toggle button").forEach((btn) => {
    btn.addEventListener("click", () => {
      map.setPaintProperty("lor-fill", "fill-color", LAYER_PAINT[btn.dataset.layer]);
      setLegend(btn.dataset.layer);
      syncToggle(btn.dataset.layer);
    });
  });
}

init().catch((err) => {
  document.getElementById("headline").textContent = "Daten konnten nicht geladen werden.";
  console.error(err);
});
