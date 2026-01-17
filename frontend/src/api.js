import { state } from "./state.js";

async function request(path, options = {}) {
  const url = state.apiBase ? `${state.apiBase}${path}` : path;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Request failed (${res.status}): ${detail}`);
  }
  return res.json();
}

export function ping() {
  return request("/health");
}

export function fetchApps() {
  return request("/app/list");
}

export function fetchKBList() {
  return request("/kb/list");
}

export function fetchKBStats(appId, kbKey) {
  return request(`/kb/${appId}/${kbKey}/stats`);
}

export function fetchKBDocuments(appId, kbKey, limit = 20, offset = 0) {
  return request(`/kb/${appId}/${kbKey}/documents?limit=${limit}&offset=${offset}`);
}

export function fetchStoresHealth() {
  return request("/stores/health");
}

export function fetchIngestionLogs(options = {}) {
  const {
    limit = 20,
    offset = 0,
    appId,
    kbKey,
    status,
  } = options;
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  if (appId) params.set("app_id", appId);
  if (kbKey) params.set("kb_key", kbKey);
  if (status) params.set("status", status);
  return request(`/ingestion/logs?${params.toString()}`);
}

export function createKBDocument(appId, kbKey, payload) {
  return request(`/kb/${appId}/${kbKey}/documents`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function replaceKBDocument(appId, kbKey, docId, payload) {
  return request(`/kb/${appId}/${kbKey}/documents/${docId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function updateKBDocument(appId, kbKey, docId, payload) {
  return request(`/kb/${appId}/${kbKey}/documents/${docId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteKBDocument(appId, kbKey, docId) {
  return request(`/kb/${appId}/${kbKey}/documents/${docId}`, {
    method: "DELETE",
  });
}

export function pushMemory(payload) {
  return request("/memory/push", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchMemorySessions(options = {}) {
  const { limit = 20, offset = 0, appId, walletId, sessionId } = options;
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  if (appId) params.set("app_id", appId);
  if (walletId) params.set("wallet_id", walletId);
  if (sessionId) params.set("session_id", sessionId);
  return request(`/memory/sessions?${params.toString()}`);
}

export function fetchMemoryContexts(memoryKey, options = {}) {
  const { limit = 20, offset = 0, includeContent = false } = options;
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  if (includeContent) params.set("include_content", "1");
  return request(`/memory/${memoryKey}/contexts?${params.toString()}`);
}

export function updateMemoryContext(uid, payload) {
  return request(`/memory/contexts/${uid}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}
