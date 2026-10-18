const body = document.body;
const state = { timeframe: body.dataset.timeframe };
const INITIAL = window.__INITIAL_CHART__ || null;

const chartEl = document.getElementById("chart");
const oscContainer = document.getElementById("osc-panes");

const mainChart = LightweightCharts.createChart(chartEl, {
  height: 460,
  layout: { background: { type: LightweightCharts.ColorType.Solid, color: "#0e1117" }, textColor: "#c9d1d9" },
  grid: { vertLines: { color: "#1c2230" }, horzLines: { color: "#1c2230" } },
  timeScale: { timeVisible: true, secondsVisible: false },
  rightPriceScale: { borderColor: "#1c2230" },
});

const candleSeries = mainChart.addSeries(LightweightCharts.CandlestickSeries, {
  upColor: "#26a69a",
  downColor: "#ef5350",
  borderVisible: false,
  wickUpColor: "#26a69a",
  wickDownColor: "#ef5350",
});

const EMA_COLORS = ["#f0b90b", "#4c9aff", "#e056fd"];

let emaSeries = [];
let bbSeries = [];
let vwapSeries = null;
let levelLines = [];
const oscCharts = {};

const OSC_SPECS = {
  rsi: {
    label: "RSI (Relative Strength Index)",
    lines: [{ field: "series", color: "#e056fd", width: 2 }],
    levels: [70, 30],
    fixedRange: [0, 100],
  },
  macd: {
    label: "MACD (Moving Average Convergence Divergence)",
    lines: [
      { field: "macd", color: "#4c9aff", width: 2 },
      { field: "signal", color: "#f0b90b", width: 1 },
    ],
    hist: { field: "hist" },
  },
  stoch: {
    label: "Stochastic Oscillator",
    lines: [
      { field: "k", color: "#4c9aff", width: 2 },
      { field: "d", color: "#f0b90b", width: 1 },
    ],
    levels: [80, 20],
    fixedRange: [0, 100],
  },
  adx: {
    label: "ADX (Average Directional Index)",
    lines: [
      { field: "adx", color: "#e056fd", width: 2 },
      { field: "plus_di", color: "#26a69a", width: 1 },
      { field: "minus_di", color: "#ef5350", width: 1 },
    ],
    levels: [25],
  },
  obv: {
    label: "OBV (On-Balance Volume)",
    lines: [{ field: "series", color: "#8b949e", width: 2 }],
  },
};

const OSC_HEIGHT = 130;

const syncCharts = [mainChart];
let suppressSync = false;

function linkChart(chart) {
  const handler = (range) => {
    if (suppressSync || !range) return;
    suppressSync = true;
    syncCharts.forEach((other) => {
      if (other !== chart) other.timeScale().setVisibleLogicalRange(range);
    });
    suppressSync = false;
  };
  chart.__syncHandler = handler;
  chart.timeScale().subscribeVisibleLogicalRangeChange(handler);
  syncCharts.push(chart);
}

function unlinkChart(chart) {
  if (chart.__syncHandler) {
    chart.timeScale().unsubscribeVisibleLogicalRangeChange(chart.__syncHandler);
  }
  const i = syncCharts.indexOf(chart);
  if (i >= 0) syncCharts.splice(i, 1);
  chart.remove();
}

linkChart(mainChart);

function syncRange() {
  const range = mainChart.timeScale().getVisibleLogicalRange();
  if (!range) return;
  suppressSync = true;
  syncCharts.forEach((chart) => {
    if (chart !== mainChart) chart.timeScale().setVisibleLogicalRange(range);
  });
  suppressSync = false;
}

function num(id, fallback) {
  const el = document.getElementById(id);
  const value = el ? parseFloat(el.value) : NaN;
  return Number.isFinite(value) ? value : fallback;
}

function on(id) {
  const el = document.getElementById(id);
  return el ? el.checked : false;
}

function buildParams() {
  const emas = [];
  if (on("ema1-on")) emas.push(num("ema1", 20));
  if (on("ema2-on")) emas.push(num("ema2", 50));
  if (on("ema3-on")) emas.push(num("ema3", 200));

  const oscs = [];
  if (on("osc-rsi-on")) oscs.push("rsi");
  if (on("osc-macd-on")) oscs.push("macd");
  if (on("osc-stoch-on")) oscs.push("stoch");
  if (on("osc-adx-on")) oscs.push("adx");
  if (on("osc-obv-on")) oscs.push("obv");

  const checks = [];
  if (on("ema-on")) {
    checks.push("regime");
    checks.push("ema_position");
  }
  if (on("bb-on")) checks.push("bollinger");
  if (on("vwap-on")) checks.push("vwap");
  if (on("osc-rsi-on")) checks.push("rsi");
  if (on("osc-macd-on")) checks.push("macd");
  if (on("osc-stoch-on")) checks.push("stoch");
  if (on("osc-adx-on")) checks.push("adx");
  if (on("osc-obv-on")) checks.push("obv");

  const params = new URLSearchParams();
  params.set("timeframe", state.timeframe);
  params.set("limit", "500");
  params.set("checks", checks.join(","));
  params.set("ema", emas.join(","));
  params.set("ema_short", String(num("ema1", 20)));
  params.set("ema_mid", String(num("ema2", 50)));
  params.set("ema_long", String(num("ema3", 200)));
  params.set("bb_period", String(num("bb-period", 20)));
  params.set("bb_std", String(num("bb-std", 2)));
  params.set("show_bb", String(on("bb-on")));
  params.set("show_vwap", String(on("vwap-on")));
  params.set("vwap_period", String(num("vwap-period", 20)));
  params.set("osc", oscs.join(","));
  params.set("rsi_period", String(num("rsi-period", 14)));
  params.set("macd_fast", String(num("macd-fast", 12)));
  params.set("macd_slow", String(num("macd-slow", 26)));
  params.set("macd_signal", String(num("macd-signal", 9)));
  params.set("stoch_k", String(num("stoch-k", 14)));
  params.set("stoch_d", String(num("stoch-d", 3)));
  params.set("stoch_smooth", String(num("stoch-smooth", 3)));
  params.set("adx_period", String(num("adx-period", 14)));
  params.set("obv_lookback", String(num("obv-lookback", 10)));
  return params;
}

function addLine(target, color, width, data) {
  const series = target.addSeries(LightweightCharts.LineSeries, {
    color,
    lineWidth: width,
    priceLineVisible: false,
    lastValueVisible: false,
    crosshairMarkerVisible: false,
  });
  series.setData(data);
  return series;
}

function clearOverlays() {
  emaSeries.forEach((s) => mainChart.removeSeries(s));
  bbSeries.forEach((s) => mainChart.removeSeries(s));
  if (vwapSeries) mainChart.removeSeries(vwapSeries);
  levelLines.forEach((line) => candleSeries.removePriceLine(line));
  emaSeries = [];
  bbSeries = [];
  vwapSeries = null;
  levelLines = [];
}

function applyLevels(levels) {
  if (!levels) return;
  if (levels.support) {
    levelLines.push(
      candleSeries.createPriceLine({
        price: levels.support,
        color: "#26a69a",
        lineWidth: 1,
        lineStyle: LightweightCharts.LineStyle.Dashed,
        axisLabelVisible: true,
        title: "S",
      })
    );
  }
  if (levels.resistance) {
    levelLines.push(
      candleSeries.createPriceLine({
        price: levels.resistance,
        color: "#ef5350",
        lineWidth: 1,
        lineStyle: LightweightCharts.LineStyle.Dashed,
        axisLabelVisible: true,
        title: "R",
      })
    );
  }
}

function renderOverlays(overlays) {
  clearOverlays();
  Object.values(overlays.ema || {}).forEach((points, i) => {
    emaSeries.push(addLine(mainChart, EMA_COLORS[i % EMA_COLORS.length], 2, points));
  });
  if (overlays.bb) {
    bbSeries.push(addLine(mainChart, "rgba(139,148,158,0.8)", 1, overlays.bb.upper));
    bbSeries.push(addLine(mainChart, "rgba(139,148,158,0.8)", 1, overlays.bb.lower));
    bbSeries.push(addLine(mainChart, "rgba(139,148,158,0.4)", 1, overlays.bb.mid));
  }
  if (overlays.vwap) {
    vwapSeries = addLine(mainChart, "#ff9800", 1, overlays.vwap);
  }
  applyLevels(overlays.levels);
}

function renderCandles(candles) {
  candleSeries.setData(
    candles.map((c) => ({
      time: c.time,
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
    }))
  );
}

function histData(points) {
  return (points || []).map((p) => ({
    time: p.time,
    value: p.value,
    color: p.value >= 0 ? "rgba(38,166,154,0.55)" : "rgba(239,83,80,0.55)",
  }));
}

function createOscChart(id) {
  const wrap = document.createElement("div");
  wrap.className = "osc-pane";
  wrap.id = "osc-" + id;

  const head = document.createElement("div");
  head.className = "osc-head";
  head.textContent = OSC_SPECS[id].label;
  wrap.appendChild(head);

  const plot = document.createElement("div");
  plot.className = "osc-plot";
  wrap.appendChild(plot);
  oscContainer.appendChild(wrap);

  const chart = LightweightCharts.createChart(plot, {
    width: chartEl.clientWidth,
    height: OSC_HEIGHT,
    layout: { background: { type: LightweightCharts.ColorType.Solid, color: "#0e1117" }, textColor: "#c9d1d9" },
    grid: { vertLines: { color: "#1c2230" }, horzLines: { color: "#1c2230" } },
    timeScale: { timeVisible: true, secondsVisible: false },
    rightPriceScale: { borderColor: "#1c2230" },
  });
  return chart;
}

function buildOsc(id, data) {
  const spec = OSC_SPECS[id];
  const chart = createOscChart(id);
  const refs = { chart, lines: {}, hist: null, priceLines: [] };

  spec.lines.forEach((line) => {
    const series = chart.addSeries(LightweightCharts.LineSeries, {
      color: line.color,
      lineWidth: line.width,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
      autoscaleInfoProvider: spec.fixedRange
        ? () => ({
            priceRange: { minValue: spec.fixedRange[0], maxValue: spec.fixedRange[1] },
          })
        : undefined,
    });
    series.setData(data[line.field] || []);
    refs.lines[line.field] = series;
  });

  if (spec.hist) {
    const hist = chart.addSeries(LightweightCharts.HistogramSeries, {
      priceLineVisible: false,
      lastValueVisible: false,
    });
    hist.setData(histData(data[spec.hist.field]));
    refs.hist = hist;
  }

  if (spec.levels) {
    const anchor = refs.lines[spec.lines[0].field];
    spec.levels.forEach((price) => {
      refs.priceLines.push(
        anchor.createPriceLine({
          price,
          color: "#555c66",
          lineWidth: 1,
          lineStyle: LightweightCharts.LineStyle.Dashed,
          axisLabelVisible: false,
          title: "",
        })
      );
    });
  }

  linkChart(chart);
  return refs;
}

function updateOsc(id, refs, data) {
  const spec = OSC_SPECS[id];
  spec.lines.forEach((line) => refs.lines[line.field].setData(data[line.field] || []));
  if (spec.hist) refs.hist.setData(histData(data[spec.hist.field]));
}

function syncOscillators(oscData) {
  oscData = oscData || {};
  Object.keys(OSC_SPECS).forEach((id) => {
    const enabled = Object.prototype.hasOwnProperty.call(oscData, id);
    const existing = oscCharts[id];
    if (enabled && !existing) {
      oscCharts[id] = buildOsc(id, oscData[id]);
    } else if (enabled && existing) {
      updateOsc(id, existing, oscData[id]);
    } else if (!enabled && existing) {
      unlinkChart(existing.chart);
      const el = document.getElementById("osc-" + id);
      if (el) el.remove();
      delete oscCharts[id];
    }
  });
  syncRange();
  resizeCharts();
}

function resizeCharts() {
  const width = chartEl.clientWidth;
  mainChart.applyOptions({ width });
  Object.values(oscCharts).forEach((refs) => refs.chart.applyOptions({ width }));
}

async function loadChart(fit) {
  const res = await fetch("/api/chart?" + buildParams().toString());
  if (!res.ok) {
    console.error("chart request failed", await res.text());
    return;
  }
  const data = await res.json();
  const range = mainChart.timeScale().getVisibleLogicalRange();
  renderCandles(data.candles);
  renderOverlays(data.overlays);
  syncOscillators(data.oscillators);
  if (fit) {
    mainChart.timeScale().fitContent();
    syncRange();
  } else if (range) {
    mainChart.timeScale().setVisibleLogicalRange(range);
    syncRange();
  }
}

async function refreshIndicators() {
  const res = await fetch("/api/overlays?" + buildParams().toString());
  if (!res.ok) {
    console.error("overlay request failed", await res.text());
    return;
  }
  const data = await res.json();
  const range = mainChart.timeScale().getVisibleLogicalRange();
  renderOverlays(data.overlays);
  syncOscillators(data.oscillators);
  if (range) mainChart.timeScale().setVisibleLogicalRange(range);
  syncRange();
}

let indicatorTimer = null;
function scheduleIndicatorRefresh() {
  clearTimeout(indicatorTimer);
  indicatorTimer = setTimeout(() => {
    refreshIndicators();
    refreshPanel();
    refreshParams();
  }, 150);
}

function refreshParams() {
  const url = "/params/review?" + buildParams().toString();
  const target = document.getElementById("params-note");
  if (!target) return;
  fetch(url)
    .then((res) => res.text())
    .then((html) => {
      target.innerHTML = html;
    });
}

function refreshPanel() {
  const url = "/analysis/view?" + buildParams().toString();
  if (window.htmx) {
    htmx.ajax("GET", url, { target: "#panel", swap: "innerHTML" });
    return;
  }
  fetch(url)
    .then((res) => res.text())
    .then((html) => {
      document.getElementById("panel").innerHTML = html;
    });
}

document.querySelectorAll(".tf").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tf").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    state.timeframe = btn.dataset.tf;
    document.getElementById("tf-label").textContent = state.timeframe;
    loadChart(true);
    refreshPanel();
    refreshParams();
  });
});

[
  "ema1", "ema2", "ema3", "bb-period", "bb-std", "vwap-period",
  "ema-on", "ema1-on", "ema2-on", "ema3-on", "bb-on", "vwap-on",
  "rsi-period", "macd-fast", "macd-slow", "macd-signal",
  "stoch-k", "stoch-d", "stoch-smooth", "adx-period", "obv-lookback",
  "osc-rsi-on", "osc-macd-on", "osc-stoch-on", "osc-adx-on", "osc-obv-on",
].forEach((id) => {
  const el = document.getElementById(id);
  if (el) el.addEventListener("change", scheduleIndicatorRefresh);
});

document.getElementById("refresh").addEventListener("click", () => {
  loadChart(false);
  refreshPanel();
});

if (INITIAL) {
  renderCandles(INITIAL.candles);
  renderOverlays(INITIAL.overlays);
  syncOscillators(INITIAL.oscillators);
  mainChart.timeScale().fitContent();
  syncRange();
} else {
  loadChart(true);
}

window.addEventListener("resize", resizeCharts);
