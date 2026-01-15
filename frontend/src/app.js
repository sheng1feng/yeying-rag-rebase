import { state, loadApiBase, setApiBase } from "./state.js";
import { mockData } from "./mock.js";
import {
  ping,
  fetchApps,
  fetchKBList,
  fetchKBStats,
  fetchKBDocuments,
  createKBDocument,
  updateKBDocument,
  deleteKBDocument,
  fetchIngestionLogs,
  pushMemory,
} from "./api.js";

const apiBaseInput = document.getElementById("api-base");
const refreshBtn = document.getElementById("refresh-btn");
const statusDot = document.getElementById("api-status-dot");
const statusText = document.getElementById("api-status-text");
const backBtn = document.getElementById("back-btn");
const appSwitch = document.getElementById("app-switch");

const appTitle = document.getElementById("app-title");
const appHeading = document.getElementById("app-heading");
const appSummary = document.getElementById("app-summary");
const appNewDoc = document.getElementById("app-new-doc");
const appIngestion = document.getElementById("app-ingestion");

const metricKbs = document.getElementById("metric-kbs");
const metricVectors = document.getElementById("metric-vectors");
const metricIngestion = document.getElementById("metric-ingestion");
const metricKbsTrend = document.getElementById("metric-kbs-trend");
const metricVectorsTrend = document.getElementById("metric-vectors-trend");
const metricIngestionTrend = document.getElementById("metric-ingestion-trend");

const kbTable = document.getElementById("kb-table");
const kbSearch = document.getElementById("kb-search");
const kbFilterToggle = document.getElementById("kb-filter-toggle");
const kbFilterPanel = document.getElementById("kb-filter-panel");
const schemaToggle = document.getElementById("kb-schema-toggle");
const schemaPanel = document.getElementById("kb-schema-panel");

const detailTitle = document.getElementById("kb-detail-title");
const detailSubtitle = document.getElementById("kb-detail-subtitle");
const detailCollection = document.getElementById("kb-detail-collection");
const detailDocs = document.getElementById("kb-detail-docs");
const detailChunks = document.getElementById("kb-detail-chunks");
const detailAccess = document.getElementById("kb-detail-access");
const detailLog = document.getElementById("kb-detail-log");

const chartBars = [
  document.getElementById("chart-bar-1"),
  document.getElementById("chart-bar-2"),
  document.getElementById("chart-bar-3"),
  document.getElementById("chart-bar-4"),
];

const docSubtitle = document.getElementById("doc-subtitle");
const docSearch = document.getElementById("doc-search");
const docRefresh = document.getElementById("doc-refresh");
const docTable = document.getElementById("doc-table");
const docPanel = document.getElementById("doc-panel");
const docPanelBody = document.getElementById("doc-panel-body");
const docToggle = document.getElementById("doc-toggle");
const docForm = document.getElementById("doc-form");
const docIdInput = document.getElementById("doc-id");
const docTextInput = document.getElementById("doc-text");
const docPropsInput = document.getElementById("doc-props");
const docReset = document.getElementById("doc-reset");
const docDelete = document.getElementById("doc-delete");
const docHint = document.getElementById("doc-hint");
const docDrawer = document.getElementById("doc-drawer");
const docDrawerBackdrop = document.getElementById("doc-drawer-backdrop");
const docDrawerClose = document.getElementById("drawer-close");
const drawerTitle = document.getElementById("drawer-title");
const drawerSubtitle = document.getElementById("drawer-subtitle");
const drawerDocId = document.getElementById("drawer-doc-id");
const drawerDocUpdated = document.getElementById("drawer-doc-updated");
const drawerDocCreated = document.getElementById("drawer-doc-created");
const drawerDocFields = document.getElementById("drawer-doc-fields");
const drawerDocMeta = document.getElementById("drawer-doc-meta");

const memoryForm = document.getElementById("memory-form");
const memoryAppId = document.getElementById("memory-app-id");
const memoryWalletId = document.getElementById("memory-wallet-id");
const memorySessionId = document.getElementById("memory-session-id");
const memoryFilename = document.getElementById("memory-filename");
const memoryDescription = document.getElementById("memory-description");
const memoryThreshold = document.getElementById("memory-threshold");
const memoryHint = document.getElementById("memory-hint");
const memoryLog = document.getElementById("memory-log");

const timeline = document.getElementById("ingestion-timeline");
const ingestionExport = document.getElementById("ingestion-export");
const ingestionHint = document.getElementById("ingestion-hint");

let currentAppId = new URLSearchParams(window.location.search).get("app_id");

function setStatus(online) {
  statusDot.style.background = online ? "#39d98a" : "#ff6a88";
  statusDot.style.boxShadow = online
    ? "0 0 12px rgba(57, 217, 138, 0.7)"
    : "0 0 12px rgba(255, 106, 136, 0.7)";
  statusText.textContent = online ? "在线" : "离线";
}

function updateUrl(appId) {
  const url = new URL(window.location.href);
  url.searchParams.set("app_id", appId);
  history.replaceState({}, "", url.toString());
}

function renderAppSwitch(apps) {
  appSwitch.innerHTML = apps
    .map((app) => `<option value="${app.app_id}">${app.app_id}</option>`)
    .join("");
  appSwitch.disabled = !apps.length;
  if (currentAppId) {
    appSwitch.value = currentAppId;
  }
}

function applyData(data) {
  state.apps = data.apps || [];
  state.knowledgeBases = data.knowledgeBases || [];
  state.ingestion = data.ingestion || [];
  state.ingestionRaw = data.ingestionRaw || [];
  state.vectors = data.vectors || 0;

  const appInfo = data.appInfo || null;
  const appLabel = appInfo ? appInfo.app_id : "未知应用";
  const statusLabel = appInfo ? appInfo.status || "未知" : "未知";

  appTitle.textContent = appLabel;
  appHeading.textContent = `${appLabel} 控制台`;
  appSummary.textContent = appInfo
    ? `状态 ${statusLabel} · 插件 ${appInfo.has_plugin ? "启用" : "缺失"}`
    : "注册表中未找到该应用。";

  metricKbs.textContent = state.knowledgeBases.length;
  metricVectors.textContent = new Intl.NumberFormat().format(state.vectors);
  metricIngestion.textContent = state.ingestionRaw.length;
  metricKbsTrend.textContent = `状态 ${statusLabel}`;
  metricVectorsTrend.textContent = state.knowledgeBases.length
    ? `${state.knowledgeBases.length} 个知识库`
    : "暂无知识库";
  metricIngestionTrend.textContent = state.ingestionRaw[0]?.created_at || "-";

  renderKbTable();
  renderKbFilters();
  renderTimeline();

  if (!state.selectedKb && state.knowledgeBases.length) {
    selectKb(state.knowledgeBases[0].id);
  }

  if (appInfo) {
    memoryAppId.value = appInfo.app_id;
  }
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
    const fallbackApp = currentAppId || mockData.apps[0]?.app_id || "unknown";
    currentAppId = fallbackApp;
    updateUrl(currentAppId);
    renderAppSwitch(mockData.apps);
    const fallbackKbs = mockData.knowledgeBases.filter((kb) => kb.app_id === currentAppId);
    const totalVectors = fallbackKbs.reduce((sum, kb) => sum + (kb.chunks || 0), 0);
    applyData({
      apps: mockData.apps,
      appInfo: mockData.apps.find((app) => app.app_id === currentAppId),
      knowledgeBases: fallbackKbs,
      ingestion: mockData.ingestion,
      ingestionRaw: mockData.ingestion,
      vectors: totalVectors,
    });
    return;
  }

  try {
    const [apps, kbList] = await Promise.all([fetchApps(), fetchKBList()]);
    if (!currentAppId && apps.length) {
      currentAppId = apps[0].app_id;
      updateUrl(currentAppId);
    }
    renderAppSwitch(apps || []);

    const appInfo = (apps || []).find((app) => app.app_id === currentAppId) || null;
    if (!appInfo) {
      applyData({ apps, appInfo: null, knowledgeBases: [], ingestion: [], ingestionRaw: [], vectors: 0 });
      return;
    }

    const appKbs = (kbList || []).filter((kb) => kb.app_id === currentAppId);
    const kbStats = await Promise.all(
      appKbs.map(async (kb) => {
        try {
          const stat = await fetchKBStats(kb.app_id, kb.kb_key);
          return {
            key: `${kb.app_id}:${kb.kb_key}`,
            count: stat.total_count,
            chunks: stat.chunk_count,
          };
        } catch (err) {
          return { key: `${kb.app_id}:${kb.kb_key}`, count: "-", chunks: "-" };
        }
      })
    );

    const statsMap = new Map(kbStats.map((item) => [item.key, item]));
    const mappedKbs = appKbs.map((kb) => {
      const id = `${kb.app_id}:${kb.kb_key}`;
      const stat = statsMap.get(id) || { count: "-", chunks: "-" };
      return {
        id,
        app_id: kb.app_id,
        kb_key: kb.kb_key,
        text_field: kb.text_field || "text",
        name: kb.kb_key,
        type: kb.kb_type || "kb",
        collection: kb.collection || "-",
        docs: stat.count,
        chunks: stat.chunks,
        owner: kb.app_id,
        access: kb.kb_type === "user_upload" ? "restricted" : "public",
        updated_at: kb.status ? `应用 ${kb.status}` : "未知",
        log: [
          `Top_k ${kb.top_k ?? "-"}`,
          `Weight ${kb.weight ?? "-"}`,
          kb.use_allowed_apps_filter ? "启用应用过滤" : "未启用应用过滤",
        ],
        histogram: [40, 56, 32, 48],
      };
    });

    const totalVectors = mappedKbs
      .map((kb) => (typeof kb.chunks === "number" ? kb.chunks : 0))
      .reduce((a, b) => a + b, 0);

    const ingestionLogs = await fetchIngestionLogs({ appId: currentAppId });
    const ingestionRaw = (ingestionLogs && ingestionLogs.items) || [];

    applyData({
      apps,
      appInfo,
      knowledgeBases: mappedKbs,
      vectors: totalVectors,
      ingestion: mapIngestion(ingestionLogs) || [],
      ingestionRaw,
    });
  } catch (err) {
    applyData({ apps: [], appInfo: null, knowledgeBases: [], ingestion: [], ingestionRaw: [], vectors: 0 });
  }
}

function renderKbTable() {
  const query = (kbSearch.value || "").toLowerCase();
  const filters = state.kbFilters;
  const rows = state.knowledgeBases
    .filter((kb) => {
      if (!query) return true;
      return (
        kb.name.toLowerCase().includes(query) ||
        kb.collection.toLowerCase().includes(query) ||
        kb.owner.toLowerCase().includes(query)
      );
    })
    .filter((kb) => {
      const ownerMatch = !filters.owners.length || filters.owners.includes(kb.owner);
      const typeMatch = !filters.types.length || filters.types.includes(kb.type);
      const accessMatch = !filters.access.length || filters.access.includes(kb.access);
      return ownerMatch && typeMatch && accessMatch;
    });

  const header = `
    <div class="table-row header">
      <div>名称</div>
      <div>类型</div>
      <div>文档数</div>
      <div>向量数</div>
      <div>集合</div>
      <div>权限</div>
    </div>
  `;

  const body = rows
    .map((kb) => {
      const active = state.selectedKb === kb.id ? "active" : "";
      const badge = kb.access === "restricted" ? "受限" : "公开";
      return `
        <div class="table-row ${active}" data-kb="${kb.id}">
          <div>
            <strong>${kb.name}</strong>
            <div class="badge">${kb.owner}</div>
          </div>
          <div>${kb.type}</div>
          <div>${kb.docs}</div>
          <div>${kb.chunks}</div>
          <div>${kb.collection}</div>
          <div>${badge}</div>
        </div>
      `;
    })
    .join("");

  kbTable.innerHTML = header + body;

  kbTable.querySelectorAll(".table-row[data-kb]").forEach((row) => {
    row.addEventListener("click", () => selectKb(row.dataset.kb));
  });
}

function renderKbFilters() {
  if (!kbFilterPanel) return;
  const owners = Array.from(new Set(state.knowledgeBases.map((kb) => kb.owner).filter(Boolean))).sort();
  const types = Array.from(new Set(state.knowledgeBases.map((kb) => kb.type).filter(Boolean))).sort();
  const access = Array.from(new Set(state.knowledgeBases.map((kb) => kb.access).filter(Boolean))).sort();
  const filters = state.kbFilters;

  if (!owners.length && !types.length && !access.length) {
    kbFilterPanel.innerHTML = "<div class=\"detail-label\">暂无可用筛选项。</div>";
    return;
  }

  const buildGroup = (label, items, selected, key) => {
    if (!items.length) return "";
    const chips = items
      .map((item) => {
        const checked = selected.includes(item) ? "checked" : "";
        return `<label class="filter-chip"><input type="checkbox" data-filter="${key}" value="${item}" ${checked} />${item}</label>`;
      })
      .join("");
    return `<div class="filter-group"><span>${label}</span>${chips}</div>`;
  };

  kbFilterPanel.innerHTML = `
    ${buildGroup("应用", owners, filters.owners, "owners")}
    ${buildGroup("类型", types, filters.types, "types")}
    ${buildGroup("权限", access, filters.access, "access")}
    <div class="filter-group">
      <button class="ghost" id="kb-filter-clear">清空筛选</button>
    </div>
  `;

  kbFilterPanel.querySelectorAll("input[data-filter]").forEach((input) => {
    input.addEventListener("change", () => {
      const next = { owners: [], types: [], access: [] };
      kbFilterPanel.querySelectorAll("input[data-filter]:checked").forEach((checked) => {
        const key = checked.dataset.filter;
        if (key && next[key]) {
          next[key].push(checked.value);
        }
      });
      state.kbFilters = next;
      renderKbTable();
    });
  });

  const clearBtn = kbFilterPanel.querySelector("#kb-filter-clear");
  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      state.kbFilters = { owners: [], types: [], access: [] };
      renderKbFilters();
      renderKbTable();
    });
  }
}

async function selectKb(id) {
  const kb = state.knowledgeBases.find((item) => item.id === id);
  if (!kb) return;
  state.selectedKb = id;
  closeDocDrawer();
  resetDocForm({ render: false });
  renderKbTable();
  if (schemaPanel) {
    schemaPanel.classList.add("hidden");
    schemaToggle.textContent = "字段结构";
  }

  detailTitle.textContent = kb.name;
  detailSubtitle.textContent = `更新 ${kb.updated_at} · 应用 ${kb.owner}`;
  detailCollection.textContent = kb.collection;
  detailDocs.textContent = kb.docs;
  detailChunks.textContent = kb.chunks;
  detailAccess.textContent = kb.access;
  detailLog.innerHTML = kb.log.map((line) => `> ${line}`).join("<br>");

  kb.histogram.forEach((value, index) => {
    const height = Math.min(100, Math.max(12, value));
    chartBars[index].style.height = `${height}%`;
  });

  await loadDocuments();
}

async function loadDocuments() {
  const kb = getSelectedKb();
  if (!kb) {
    docSubtitle.textContent = "请选择知识库加载文档，点击行查看详情。";
    state.documents = [];
    state.docTotal = 0;
    state.docColumns = [];
    renderDocTable();
    resetDocForm({ render: false });
    updateDocDrawerMeta(null);
    return;
  }

  docSubtitle.textContent = `集合 ${kb.collection} · 文本字段 ${kb.text_field} · 点击行查看详情`;
  try {
    const res = await fetchKBDocuments(kb.app_id, kb.kb_key, 20, 0);
    state.documents = res.items || [];
    state.docTotal = res.total ?? 0;
    state.docColumns = buildDocColumns(state.documents, kb.text_field);
    const labelColumns = state.docColumns.length ? state.docColumns : ["id", kb.text_field || "text"];
    const columnsLabel =
      labelColumns.length > 6
        ? `${labelColumns.slice(0, 6).join(", ")} ...`
        : labelColumns.join(", ");
    docSubtitle.textContent = `集合 ${kb.collection} · 文本字段 ${kb.text_field} · 总数 ${state.docTotal} · 列: ${columnsLabel} · 点击行查看详情`;
    renderDocTable();
    syncDocSelection();
  } catch (err) {
    docHint.textContent = `加载失败: ${err.message}`;
    state.documents = [];
    state.docTotal = 0;
    state.docColumns = [];
    renderDocTable();
    resetDocForm({ render: false });
    updateDocDrawerMeta(null);
  }
}

function renderDocTable() {
  const query = (docSearch.value || "").toLowerCase();
  const rows = state.documents.filter((doc) => {
    if (!query) return true;
    const text = JSON.stringify(doc.properties || {}).toLowerCase();
    return doc.id.toLowerCase().includes(query) || text.includes(query);
  });

  const kb = getSelectedKb();
  const textField = kb?.text_field || "text";
  const columns = state.docColumns.length ? state.docColumns : ["id", textField];
  const columnTemplate = buildDocGridTemplate(columns.length);

  const header = `
    <div class="table-row header" style="--doc-columns: ${columnTemplate}">
      ${columns
        .map((col) => (col === "id" ? "<div>ID</div>" : `<div>${escapeHtml(col)}</div>`))
        .join("")}
    </div>
  `;

  const body = rows
    .map((doc) => {
      const active = state.selectedDocId === doc.id ? "active" : "";
      const cells = columns
        .map((col) => {
          if (col === "id") {
            const safeId = escapeHtml(doc.id);
            return `<div class="cell-id" title="${safeId}">${safeId}</div>`;
          }
          const value = doc.properties ? doc.properties[col] : undefined;
          return `<div>${renderCell(value)}</div>`;
        })
        .join("");
      return `
        <div class="table-row ${active}" data-doc="${doc.id}" style="--doc-columns: ${columnTemplate}">
          ${cells}
        </div>
      `;
    })
    .join("");

  docTable.innerHTML = header + body;

  docTable.querySelectorAll(".table-row[data-doc]").forEach((row) => {
    row.addEventListener("click", () => selectDoc(row.dataset.doc));
  });
}

function setDocPanelCollapsed(collapsed) {
  if (!docPanel || !docPanelBody || !docToggle) return;
  docPanel.classList.toggle("collapsed", collapsed);
  docPanelBody.setAttribute("aria-hidden", collapsed ? "true" : "false");
  docToggle.textContent = collapsed ? "展开" : "收起";
  docToggle.setAttribute("aria-expanded", collapsed ? "false" : "true");
}

function toggleDocPanel() {
  if (!docPanel) return;
  setDocPanelCollapsed(!docPanel.classList.contains("collapsed"));
}

function syncDocSelection() {
  if (!state.selectedDocId) {
    if (docDelete) {
      docDelete.disabled = true;
    }
    return;
  }
  const doc = state.documents.find((item) => item.id === state.selectedDocId);
  if (!doc) {
    resetDocForm({ render: false });
    updateDocDrawerMeta(null);
    return;
  }
  setDocFormFields(doc);
  updateDocDrawerMeta(doc);
}

function getDocText(doc) {
  const kb = getSelectedKb();
  const textField = kb?.text_field || "text";
  const props = doc.properties || {};
  return props[textField] || props.text || props.content || "";
}

function setDrawerOpen(isOpen) {
  if (!docDrawer) return;
  docDrawer.classList.toggle("open", isOpen);
  docDrawer.setAttribute("aria-hidden", isOpen ? "false" : "true");
  document.body.classList.toggle("drawer-open", isOpen);
}

function closeDocDrawer() {
  setDrawerOpen(false);
}

function setDocFormFields(doc) {
  docIdInput.value = doc ? doc.id : "";
  docTextInput.value = doc ? String(getDocText(doc) || "") : "";
  docPropsInput.value = doc ? JSON.stringify(doc.properties || {}, null, 2) : "";
  docHint.textContent = "";
  if (docDelete) {
    docDelete.disabled = !doc;
  }
}

function updateDocDrawerMeta(doc) {
  if (!drawerTitle || !drawerDocMeta) return;
  const kb = getSelectedKb();
  const textField = kb?.text_field || "text";

  if (!doc) {
    drawerTitle.textContent = "新建文档";
    drawerSubtitle.textContent = kb
      ? `集合 ${kb.collection} · 文本字段 ${textField}`
      : "请选择知识库后新建文档。";
    drawerDocId.textContent = "-";
    drawerDocUpdated.textContent = "-";
    drawerDocCreated.textContent = "-";
    drawerDocFields.textContent = "0";
    drawerDocMeta.textContent = "填写字段并保存后可查看文档详情。";
    return;
  }

  const props = doc.properties || {};
  const fieldCount = Object.keys(props).length;
  drawerTitle.textContent = "文档详情";
  drawerSubtitle.textContent = kb ? `集合 ${kb.collection} · 字段 ${fieldCount}` : "文档详情";
  drawerDocId.textContent = doc.id || "-";
  drawerDocUpdated.textContent = doc.updated_at || "-";
  drawerDocCreated.textContent = doc.created_at || "-";
  drawerDocFields.textContent = String(fieldCount);
  drawerDocMeta.innerHTML = renderDocMeta(props, textField);
}

function renderDocMeta(props, textField) {
  const entries = Object.entries(props || {});
  if (!entries.length) {
    return "该文档暂无属性字段。";
  }
  return entries
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([key, value]) => {
      const type = normalizeSchemaType(value);
      const sample = escapeHtml(formatSchemaValue(value));
      const label = escapeHtml(key);
      const mark = key === textField ? "（主文本）" : "";
      return `<div><strong>${label}${mark}</strong> (${type})<br /><span>${sample}</span></div>`;
    })
    .join("<br />");
}

function openNewDocDrawer() {
  resetDocForm();
  updateDocDrawerMeta(null);
  setDrawerOpen(true);
  docTextInput.focus();
}

function selectDoc(docId) {
  const doc = state.documents.find((item) => item.id === docId);
  if (!doc) return;
  state.selectedDocId = docId;
  setDocFormFields(doc);
  renderDocTable();
  updateDocDrawerMeta(doc);
  setDrawerOpen(true);
}

function getSelectedKb() {
  return state.knowledgeBases.find((kb) => kb.id === state.selectedKb);
}

function buildDocColumns(docs, textField) {
  const counts = new Map();
  docs.forEach((doc) => {
    const props = doc.properties || {};
    Object.keys(props).forEach((key) => {
      if (key === textField) return;
      counts.set(key, (counts.get(key) || 0) + 1);
    });
  });
  const extraKeys = Array.from(counts.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 4)
    .map(([key]) => key);
  return ["id", textField || "text", ...extraKeys];
}

function buildDocGridTemplate(count) {
  if (count <= 2) {
    return "1.2fr 2.6fr";
  }
  const columns = ["1.2fr", "2.6fr"];
  for (let i = 2; i < count; i += 1) {
    columns.push("1fr");
  }
  return columns.join(" ");
}

function renderCell(value) {
  if (value === null || value === undefined || value === "") {
    return "<span class=\"cell-muted\">-</span>";
  }
  let text = value;
  if (typeof value !== "string") {
    try {
      text = JSON.stringify(value);
    } catch (err) {
      text = String(value);
    }
  }
  const output = text.length > 160 ? `${text.slice(0, 160)}...` : text;
  return `<span title="${escapeHtml(text)}">${escapeHtml(output)}</span>`;
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

async function toggleSchema() {
  const kb = getSelectedKb();
  if (!kb) {
    schemaPanel.textContent = "请先选择知识库。";
    schemaPanel.classList.remove("hidden");
    schemaToggle.textContent = "收起字段";
    return;
  }
  const isHidden = schemaPanel.classList.contains("hidden");
  if (!isHidden) {
    schemaPanel.classList.add("hidden");
    schemaToggle.textContent = "字段结构";
    return;
  }
  schemaToggle.textContent = "收起字段";
  schemaPanel.classList.remove("hidden");
  schemaPanel.textContent = "字段结构加载中...";

  let docs = state.documents;
  if (!docs.length) {
    try {
      const res = await fetchKBDocuments(kb.app_id, kb.kb_key, 25, 0);
      docs = res.items || [];
    } catch (err) {
      schemaPanel.textContent = `加载失败: ${err.message}`;
      return;
    }
  }

  const schema = inferSchema(docs);
  schemaPanel.innerHTML = renderSchema(schema);
}

function inferSchema(docs) {
  const map = new Map();
  docs.forEach((doc) => {
    const props = doc.properties || {};
    Object.entries(props).forEach(([key, value]) => {
      const entry = map.get(key) || { types: new Set(), example: null };
      const type = normalizeSchemaType(value);
      entry.types.add(type);
      if (entry.example === null && value !== null && value !== undefined) {
        entry.example = value;
      }
      map.set(key, entry);
    });
  });

  return Array.from(map.entries())
    .map(([name, entry]) => ({
      name,
      types: Array.from(entry.types.values()).sort(),
      example: entry.example,
    }))
    .sort((a, b) => a.name.localeCompare(b.name));
}

function normalizeSchemaType(value) {
  if (value === null) return "空值";
  if (Array.isArray(value)) return "数组";
  const type = typeof value;
  if (type === "object") return "对象";
  if (type === "string") return "字符串";
  if (type === "number") return "数值";
  if (type === "boolean") return "布尔";
  return "其他";
}

function renderSchema(schema) {
  if (!schema.length) {
    return "<div>暂无文档用于推断字段结构。</div>";
  }
  return schema
    .map((field) => {
      const types = escapeHtml(field.types.join(" | "));
      const example = escapeHtml(formatSchemaValue(field.example));
      return `<div><strong>${escapeHtml(field.name)}</strong> (${types})<br /><span>${example}</span></div>`;
    })
    .join("<br />");
}

function formatSchemaValue(value) {
  if (value === null || value === undefined) return "-";
  try {
    const raw = typeof value === "string" ? value : JSON.stringify(value);
    return raw.length > 140 ? `${raw.slice(0, 140)}...` : raw;
  } catch (err) {
    return String(value);
  }
}

function renderTimeline() {
  ingestionHint.textContent = "";
  if (!state.ingestion.length) {
    timeline.innerHTML = "<div class=\"timeline-item\">暂无摄取事件。</div>";
    return;
  }
  timeline.innerHTML = state.ingestion
    .map(
      (item) => `
      <div class="timeline-item">
        <strong>${item.title}</strong>
        <span>${item.time}</span>
        <span>${item.meta}</span>
      </div>
    `
    )
    .join("");
}

function mapIngestion(payload) {
  if (!payload || !Array.isArray(payload.items)) return null;
  return payload.items.slice(0, 6).map((item) => ({
    title: `${item.status.toUpperCase()} ${item.kb_key || ""}`.trim(),
    time: item.created_at || "-",
    meta: item.message || item.collection || "",
  }));
}

function resetDocForm(options = {}) {
  const { render = true } = options;
  state.selectedDocId = null;
  setDocFormFields(null);
  if (render) {
    renderDocTable();
  }
}

async function handleDocSubmit(event) {
  event.preventDefault();
  const kb = getSelectedKb();
  if (!kb) {
    docHint.textContent = "请先选择知识库。";
    return;
  }

  let props = {};
  if (docPropsInput.value.trim()) {
    try {
      props = JSON.parse(docPropsInput.value);
    } catch (err) {
      docHint.textContent = "属性 JSON 格式无效。";
      return;
    }
  }

  const payload = {
    text: docTextInput.value.trim() || null,
    properties: props,
  };

  const docId = docIdInput.value.trim();
  try {
    if (state.selectedDocId) {
      await updateKBDocument(kb.app_id, kb.kb_key, docId || state.selectedDocId, payload);
      docHint.textContent = "文档已更新。";
    } else {
      await createKBDocument(kb.app_id, kb.kb_key, { ...payload, id: docId || null });
      docHint.textContent = "文档已创建。";
    }
    await loadDocuments();
  } catch (err) {
    docHint.textContent = `保存失败: ${err.message}`;
  }
}

async function handleDocDelete() {
  const kb = getSelectedKb();
  if (!kb || !state.selectedDocId) {
    docHint.textContent = "请先选择文档。";
    return;
  }
  try {
    await deleteKBDocument(kb.app_id, kb.kb_key, state.selectedDocId);
    docHint.textContent = "文档已删除。";
    resetDocForm();
    updateDocDrawerMeta(null);
    await loadDocuments();
  } catch (err) {
    docHint.textContent = `删除失败: ${err.message}`;
  }
}

async function handleMemorySubmit(event) {
  event.preventDefault();
  const appId = memoryAppId.value.trim();
  const walletId = memoryWalletId.value.trim();
  const sessionId = memorySessionId.value.trim();
  const filename = memoryFilename.value.trim();
  const description = memoryDescription.value.trim();
  const thresholdRaw = memoryThreshold.value.trim();

  if (!appId || !walletId || !sessionId || !filename) {
    memoryHint.textContent = "应用 ID、钱包 ID、会话 ID 与文件路径为必填。";
    return;
  }

  const payload = {
    app_id: appId,
    wallet_id: walletId,
    session_id: sessionId,
    filename,
    description: description || null,
  };

  if (thresholdRaw) {
    const parsed = Number.parseInt(thresholdRaw, 10);
    if (Number.isNaN(parsed)) {
      memoryHint.textContent = "摘要阈值必须是数字。";
      return;
    }
    payload.summary_threshold = parsed;
  }

  try {
    const res = await pushMemory(payload);
    memoryHint.textContent = "记忆写入完成。";
    memoryLog.textContent = JSON.stringify(res, null, 2);
  } catch (err) {
    memoryHint.textContent = `写入失败: ${err.message}`;
  }
}

function exportIngestionLogs() {
  const payload = state.ingestionRaw.length ? state.ingestionRaw : state.ingestion;
  if (!payload.length) {
    ingestionHint.textContent = "没有可导出的摄取日志。";
    return;
  }
  ingestionHint.textContent = "";
  const blob = new Blob([JSON.stringify(payload, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `ingestion-${Date.now()}.json`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function scrollToSection(section) {
  const target = document.querySelector(`[data-section="${section}"]`);
  if (!target) return;
  target.scrollIntoView({ behavior: "smooth", block: "start" });
}

apiBaseInput.addEventListener("change", (event) => {
  setApiBase(event.target.value.trim());
  loadData();
});
refreshBtn.addEventListener("click", () => loadData());
backBtn.addEventListener("click", () => {
  window.location.href = "./index.html";
});
appSwitch.addEventListener("change", (event) => {
  const nextApp = event.target.value;
  if (!nextApp) return;
  window.location.href = `./app.html?app_id=${encodeURIComponent(nextApp)}`;
});
appNewDoc.addEventListener("click", () => {
  scrollToSection("documents");
  openNewDocDrawer();
});
appIngestion.addEventListener("click", () => {
  scrollToSection("ingestion");
});
kbFilterToggle.addEventListener("click", () => {
  kbFilterPanel.classList.toggle("hidden");
});
schemaToggle.addEventListener("click", () => toggleSchema());
kbSearch.addEventListener("input", () => renderKbTable());
docSearch.addEventListener("input", () => renderDocTable());
docRefresh.addEventListener("click", () => loadDocuments());
if (docToggle) {
  docToggle.addEventListener("click", () => toggleDocPanel());
}
docReset.addEventListener("click", () => openNewDocDrawer());
docDelete.addEventListener("click", () => handleDocDelete());
docForm.addEventListener("submit", handleDocSubmit);
memoryForm.addEventListener("submit", handleMemorySubmit);
ingestionExport.addEventListener("click", () => exportIngestionLogs());
if (docDrawerBackdrop) {
  docDrawerBackdrop.addEventListener("click", () => closeDocDrawer());
}
if (docDrawerClose) {
  docDrawerClose.addEventListener("click", () => closeDocDrawer());
}
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && docDrawer?.classList.contains("open")) {
    closeDocDrawer();
  }
});

apiBaseInput.value = loadApiBase();
loadData();
