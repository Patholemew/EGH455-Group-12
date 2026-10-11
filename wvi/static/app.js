"use strict";

const page = document.body.dataset.page;
const lcdButtons = document.querySelectorAll("[data-lcd-pane]");
const lcdStatus = document.getElementById("lcd-status");
const lcdError = document.getElementById("lcd-error");
let lcdPending = false;
let lcdRequestVersion = 0;
let targetSpeech = null;

const metrics = [
  "temperature_c", "pressure_hpa", "humidity_pct", "light_lux",
  "gas_reducing", "gas_oxidising", "gas_ammonia",
];

const chartKeys = ["temperature_c", "humidity_pct", "pressure_hpa", "light_lux"];

const chartLabels = {
  temperature_c: "Temperature",
  humidity_pct: "Humidity",
  pressure_hpa: "Pressure",
  light_lux: "Light",
};

function setBadge(id, message, state) {
  const badge = document.getElementById(id);
  badge.textContent = message;
  badge.className = "badge " + state;
}

function describe(row) {
  if (row.type === "valve") return "Valve: " + (row.valve_state || "unknown");
  if (row.type === "aruco") return "ArUco marker " + row.marker_id;
  if (row.type === "gauge") {
    const reading = row.gauge_reading;
    return "Gauge: " + (Number.isFinite(reading) ? reading.toFixed(2) : "N/A")
      + (row.gauge_unit ? " " + row.gauge_unit : "");
  }
  return row.type || "Unknown target";
}

function showDetectionAlert(targets, video) {
  const alert = document.getElementById("detection-alert");
  const visible = video.available && !video.stale
    ? targets.filter(target => !target.stale) : [];
  const message = visible.length
    ? visible.map(describe).join(" · ")
    : video.available && !video.stale ? "No current targets." : "Waiting for a live camera feed.";
  if (alert.textContent !== message) alert.textContent = message;
  document.getElementById("target-panel").classList.toggle("has-targets", visible.length > 0);
  if (targetSpeech) targetSpeech.update(visible);
}

function showLcdSelection(lcd) {
  for (const button of lcdButtons) {
    button.setAttribute("aria-pressed", String(Number(button.dataset.lcdPane) === lcd.pane));
  }
  lcdStatus.textContent = "Selected: " + lcd.label;
}

async function selectLcdPane(pane) {
  if (lcdPending) return;
  lcdPending = true;
  lcdRequestVersion += 1;
  lcdError.hidden = true;
  for (const button of lcdButtons) button.disabled = true;
  lcdStatus.textContent = "Selecting LCD screen…";
  try {
    const response = await fetch("/api/lcd", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({pane}),
      signal: AbortSignal.timeout(5000),
    });
    if (!response.ok) throw new Error("LCD request failed: " + response.status);
    showLcdSelection(await response.json());
  } catch (error) {
    lcdStatus.textContent = "LCD selection unconfirmed.";
    lcdError.textContent = "Could not confirm the LCD selection. Try again.";
    lcdError.hidden = false;
  } finally {
    // Also discard polls started while this command was being saved.
    lcdRequestVersion += 1;
    lcdPending = false;
    for (const button of lcdButtons) button.disabled = false;
  }
}

async function refresh() {
  const lcdVersion = lcdRequestVersion;
  const response = await fetch("/api/data", {cache: "no-store", signal: AbortSignal.timeout(5000)});
  if (!response.ok) throw new Error("Request failed: " + response.status);
  const data = await response.json();
  // Ignore a poll started before a newer button selection.
  if (!lcdPending && lcdVersion === lcdRequestVersion) showLcdSelection(data.lcd);

  const video = data.video;
  setBadge("video-state",
    !video.available ? "No frame"
      : video.age_seconds === null ? "No timestamp"
      : video.stale ? "Stale" : "Receiving",
    video.stale ? "stale" : "live");

  showDetectionAlert(data.targets, data.video);
  
  if (!data.air) {
    setBadge("air-state", "Waiting", "");
    document.getElementById("sensor-updated").textContent = "Waiting for sensor readings.";
    return;
  }

  document.getElementById("sensor-updated").textContent =
    "Last sample: " + new Date(data.air.captured_at * 1000).toLocaleString();

  for (const key of metrics) {
    document.getElementById(key).textContent = data.air[key].toFixed(1);
  }

  setBadge("air-state",
    data.air.stale ? "Stale" : "Receiving",
    data.air.stale ? "stale" : "live");
}

async function loop() {
  try {
    await refresh();
  } catch (error) {
    if (!lcdPending) lcdStatus.textContent = "LCD controls: connection lost.";
    showDetectionAlert([], {available: false, stale: true});
    setBadge("air-state", "Connection lost", "error");
    setBadge("video-state", "Connection lost", "error");
  }
  setTimeout(loop, 1000);
}

if (page === "dashboard") {
  targetSpeech = new TargetSpeech(document.getElementById("voice-status"));
  for (const button of lcdButtons) {
    button.addEventListener("click", () => selectLcdPane(Number(button.dataset.lcdPane)));
  }
  loop();

  const frame = document.getElementById("live-video");
  const placeholder = document.getElementById("camera-placeholder");
  frame.addEventListener("load", () => {
    frame.hidden = false;
    placeholder.hidden = true;
  });
  frame.addEventListener("error", () => {
    frame.hidden = true;
    placeholder.hidden = false;
  });
  setInterval(() => {
    frame.src = "/live.jpg?t=" + Date.now();
  }, 100);
}

if (page === "charts") {
  const charts = {};
  let range = "10";

  function makeChart(key) {
    return new Chart(document.getElementById("chart-" + key), {
      type: "line",
      data: {labels: [], datasets: [{
        data: [], borderColor: "#007d83", borderWidth: 2, pointRadius: 0, tension: 0.12,
      }]},
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        plugins: {legend: {display: false}},
        scales: {x: {ticks: {maxTicksLimit: 6, maxRotation: 0}}},
      },
    });
  }

  for (const key of chartKeys) {
    charts[key] = makeChart(key);
  }

  async function drawCharts() {
    const response = await fetch("/api/history?minutes=" + range, {cache: "no-store"});
    if (!response.ok) throw new Error("History request failed");
    const data = await response.json();

    const times = data.rows.map(row => new Date(row.captured_at * 1000).toLocaleTimeString());
    const latest = data.rows.length ? data.rows[data.rows.length - 1] : null;

    for (const key of chartKeys) {
      const chart = charts[key];
      chart.data.labels = times;
      chart.data.datasets[0].data = data.rows.map(row => row[key]);
      chart.update("none");

      document.getElementById("title-" + key).textContent =
        latest ? chartLabels[key] + ": " + latest[key] : chartLabels[key];
    }
  }

  for (const button of document.querySelectorAll(".range-buttons button")) {
    button.addEventListener("click", () => {
      range = button.dataset.minutes;
      document.querySelector(".range-buttons .active").classList.remove("active");
      button.classList.add("active");
      drawCharts();
    });
  }

  async function chartLoop() {
    try {
      await drawCharts();
    } catch (error) {
      console.error(error);
    }
    setTimeout(chartLoop, 10000);
  }

  chartLoop();
}

if (page === "targets") {
  let filter = "all";

  function cameraPosition(row) {
    if (row.type !== "aruco") return "—";
    return ["x", "y", "z"].map(axis =>
      axis.toUpperCase() + ": "
      + (Number.isFinite(row[axis]) ? row[axis].toFixed(3) : "N/A")
    ).join(", ");
  }

  function cell(text) {
    const td = document.createElement("td");
    td.textContent = text;
    return td;
  }

  function imageCell(row) {
    const td = document.createElement("td");
    if (!row.image_filename) {
      td.textContent = "No capture";
      return td;
    }
    const link = document.createElement("a");
    link.href = "/snapshots/" + encodeURIComponent(row.image_filename);
    link.target = "_blank";
    link.rel = "noopener";

    const image = document.createElement("img");
    image.src = link.href;
    image.alt = describe(row) + " capture";
    image.className = "thumb";
    image.loading = "lazy";
    image.onerror = () => link.replaceChildren(document.createTextNode("Capture unavailable"));

    link.append(image);
    td.append(link);
    return td;
  }

  async function loadTargets() {
    const response = await fetch("/api/targets?type=" + filter, {cache: "no-store"});
    if (!response.ok) throw new Error("Targets request failed");
    const data = await response.json();

    const body = document.getElementById("targets-body");
    body.replaceChildren();

    for (const row of data.rows) {
      const tr = document.createElement("tr");
      tr.append(
        imageCell(row),
        cell(new Date(row.captured_at * 1000).toLocaleTimeString()),
        cell(describe(row)),
        cell(cameraPosition(row)),
      );
      body.append(tr);
    }
  }

  for (const button of document.querySelectorAll(".range-buttons button")) {
    button.addEventListener("click", () => {
      filter = button.dataset.type;
      document.querySelector(".range-buttons .active").classList.remove("active");
      button.classList.add("active");
      loadTargets();
    });
  }

  async function targetsLoop() {
    try {
      await loadTargets();
    } catch (error) {
      console.error(error);
    }
    setTimeout(targetsLoop, 1000);
  }

  targetsLoop();
}
if (page === "logs") {
  let source = "all";

  function cell(text) {
    const td = document.createElement("td");
    td.textContent = text;
    return td;
  }

  async function loadLogs() {
    const response = await fetch("/api/logs?source=" + source, {cache: "no-store"});
    if (!response.ok) throw new Error("Logs request failed");
    const data = await response.json();

    const body = document.getElementById("logs-body");
    body.replaceChildren();

    for (const row of data.rows) {
      const tr = document.createElement("tr");
      tr.append(
        cell(new Date(row.time * 1000).toLocaleTimeString()),
        cell(row.source),
        cell(row.message),
      );
      body.append(tr);
    }

    const span = Math.floor(data.heartbeat.span_seconds);
    document.getElementById("heartbeat-span").textContent =
      Math.floor(span / 60) + "m " + (span % 60) + "s";
    document.getElementById("heartbeat-count").textContent = data.heartbeat.count;
  }

  for (const button of document.querySelectorAll(".range-buttons button")) {
    button.addEventListener("click", () => {
      source = button.dataset.source;
      document.querySelector(".range-buttons .active").classList.remove("active");
      button.classList.add("active");
      loadLogs();
    });
  }

  async function logsLoop() {
    try {
      await loadLogs();
    } catch (error) {
      console.error(error);
    }
    setTimeout(logsLoop, 10000);
  }

  logsLoop();
}
