export const state = {
  apiBase: "",
  apps: [],
  knowledgeBases: [],
  documents: [],
  docColumns: [],
  docTotal: 0,
  stores: [],
  ingestion: [],
  ingestionRaw: [],
  vectors: 0,
  selectedKb: null,
  selectedDocId: null,
  selectedAppId: null,
  kbFilters: {
    owners: [],
    types: [],
    access: [],
  },
};

export function loadApiBase() {
  const stored = localStorage.getItem("rag_api_base") || "";
  state.apiBase = stored;
  return stored;
}

export function setApiBase(value) {
  state.apiBase = value;
  localStorage.setItem("rag_api_base", value);
}
