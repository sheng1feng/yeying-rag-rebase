import { state, loadApiBase, setApiBase } from "./state.js";
import { mockData } from "./mock.js";
import { ping, fetchStoresHealth } from "./api.js";

const apiBaseInput = document.getElementById("api-base");
const refreshBtn = document.getElementById("refresh-btn");
const statusDot = document.getElementById("api-status-dot");
const statusText = document.getElementById("api-status-text");
const backBtn = document.getElementById("back-btn");
const storesRefresh = document.getElementById("stores-refresh");
const storesExport = document.getElementById("stores-export");

const metricStores = document.getElementById("metric-stores");
const metricHealthy = document.getElementById("metric-healthy");
const metricStoresTrend = document.getElementById("metric-stores-trend");
const metricHealthyTrend = document.getElementById("metric-healthy-trend");

const storeGrid = document.getElementById("store-grid");
const storeHint = document.getElementById("store-hint");

function setStatus(online) {
  statusDot.style.background = online ? "#39d98a" : "#ff6a88";
  statusDot.style.boxShadow = online
    ? "0 0 12px rgba(57, 217, 138, 0.7)"
    : "0 0 12px rgba(255, 106, 136, 0.7)";
  statusText.textContent = online ? "在线" : "离线";
}

function applyData(data) {
  state.stores = data.stores || [];
  metricStores.textContent = state.stores.length;
  const healthy = state.stores.filter((store) => store.status === "ok" || store.status === "configured").length;
  metricHealthy.textContent = healthy;
  metricStoresTrend.textContent = state.stores.length ? "在线" : "暂无存储";
  metricHealthyTrend.textContent = `${healthy}/${state.stores.length} 正常`;

  renderStores();
}

async function loadData() {
  let online = false;
  try {
    await ping();
    online = true;
  } catch (err) {
    online = false;
  }
  setStatus(online);

  if (!online) {
    applyData({ stores: mockData.stores });
    return;
  }

  try {
    const storesHealth = await fetchStoresHealth();
    applyData({ stores: mapStores(storesHealth) || [] });
  } catch (err) {
    storeHint.textContent = `加载失败: ${err.message}`;
    applyData({ stores: [] });
  }
}

function renderStores() {
  storeHint.textContent = "";
  if (!state.stores.length) {
    storeGrid.innerHTML = "<div class=\"detail-label\">暂无存储数据。</div>";
    return;
  }
  storeGrid.innerHTML = state.stores
    .map(
      (store) => `
      <div class="store-card">
        <h3>${store.name}</h3>
        <span>${store.description}</span>
        <div class="badge">${formatStatus(store.status)} · ${store.latency}</div>
      </div>
    `
    )
    .join("");
}

function mapStores(payload) {
  if (!payload || !Array.isArray(payload.stores)) return null;
  return payload.stores.map((store) => ({
    name: store.name.toUpperCase(),
    status: store.status,
    description: store.details || "无详情",
    latency: "无",
  }));
}

function exportStores() {
  if (!state.stores.length) {
    storeHint.textContent = "没有可导出的存储数据。";
    return;
  }
  const blob = new Blob([JSON.stringify(state.stores, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `stores-${Date.now()}.json`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function formatStatus(status) {
  const normalized = String(status || "").toLowerCase();
  if (normalized === "ok") return "正常";
  if (normalized === "configured") return "已配置";
  if (normalized === "disabled") return "未启用";
  if (normalized === "error") return "异常";
  return status || "-";
}

apiBaseInput.addEventListener("change", (event) => {
  setApiBase(event.target.value.trim());
  loadData();
});
refreshBtn.addEventListener("click", () => loadData());
storesRefresh.addEventListener("click", () => loadData());
storesExport.addEventListener("click", () => exportStores());
backBtn.addEventListener("click", () => {
  window.location.href = "./index.html";
});

apiBaseInput.value = loadApiBase();
loadData();
