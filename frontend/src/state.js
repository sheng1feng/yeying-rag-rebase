export const state = {
  apiBase: "",
  apps: [],
  knowledgeBases: [],
  documents: [],
  docColumns: [],
  docTotal: 0,
  docPageSize: 20,
  docPageOffset: 0,
  docVisibleColumns: [],
  docSort: null,
  selectedDocIds: new Set(),
  stores: [],
  ingestion: [],
  ingestionRaw: [],
  vectors: 0,
  selectedKb: null,
  selectedDocId: null,
  selectedAppId: null,
  memorySessions: [],
  memorySessionTotal: 0,
  memoryContexts: [],
  memoryContextTotal: 0,
  selectedMemoryKey: null,
  selectedMemoryContextId: null,
  memoryContextSnapshot: null,
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
