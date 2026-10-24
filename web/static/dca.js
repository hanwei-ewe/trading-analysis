function renderDcaChart(points) {
  const el = document.getElementById("dca-chart");
  if (!el || !window.LightweightCharts) return;
  el.innerHTML = "";
  if (!points || !points.length) return;
  const chart = LightweightCharts.createChart(el, {
    height: 280,
    layout: { background: { type: LightweightCharts.ColorType.Solid, color: "#0e1117" }, textColor: "#c9d1d9" },
    grid: { vertLines: { color: "#1c2230" }, horzLines: { color: "#1c2230" } },
    timeScale: { timeVisible: true, secondsVisible: false },
    rightPriceScale: { borderColor: "#1c2230" },
  });
  const wealth = chart.addSeries(LightweightCharts.LineSeries, {
    color: "#26a69a",
    lineWidth: 2,
    priceLineVisible: false,
    lastValueVisible: true,
  });
  wealth.setData(
    points.map((point) => ({
      time: Math.floor(new Date(point.time).getTime() / 1000),
      value: point.wealth,
    }))
  );
  const resize = () => chart.applyOptions({ width: el.clientWidth });
  resize();
  window.addEventListener("resize", resize, { passive: true });
}

window.renderDcaChart = renderDcaChart;
