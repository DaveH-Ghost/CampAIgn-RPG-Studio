/** Lorebooks tab — load, list, edit ST-format lorebooks (V0.5.0). */

import {
  createLorebook,
  deleteLorebook,
  downloadLorebook,
  getLorebook,
  getLorebooks,
  getLorebookScanConfig,
  loadDemoLorebook,
  putLorebook,
  putLorebookScanConfig,
  uploadLorebook,
} from "./api.js";

let showToast = () => {};
let onLorebooksChanged = () => {};
let getActiveAgentId = () => null;

let listEl;
let listEmptyEl;
let uploadInput;
let uploadBtn;
let createBtn;
let loadDemoBtn;
let editorPanel;
let editorTitle;
let editorCloseBtn;
let editorStatus;
let editorEntries;
let editorSaveBtn;
let editorError;
let expandAllBtn;
let collapseAllBtn;
let addEntryBtn;
let editorDownloadBtn;
let scanSourcesEl;
let scanAgentEl;

/** @type {Record<string, boolean>} */
let scanConfigState = {};

/** @type {string | null} */
let editingBookId = null;
/** @type {object | null} */
let editingBook = null;

export function initLorebooks({
  showToastFn,
  onLorebooksChangedFn,
  getActiveAgentIdFn,
}) {
  showToast = showToastFn;
  onLorebooksChanged = onLorebooksChangedFn ?? onLorebooksChanged;
  getActiveAgentId = getActiveAgentIdFn ?? getActiveAgentId;

  listEl = document.getElementById("lorebooks-list");
  listEmptyEl = document.getElementById("lorebooks-list-empty");
  uploadInput = document.getElementById("lorebook-upload-input");
  uploadBtn = document.getElementById("lorebook-upload-btn");
  createBtn = document.getElementById("lorebook-create-btn");
  loadDemoBtn = document.getElementById("lorebook-load-demo-btn");
  editorPanel = document.getElementById("lorebook-editor");
  editorTitle = document.getElementById("lorebook-editor-title");
  editorCloseBtn = document.getElementById("lorebook-editor-close");
  editorStatus = document.getElementById("lorebook-editor-status");
  editorEntries = document.getElementById("lorebook-entries");
  editorSaveBtn = document.getElementById("lorebook-editor-save");
  editorError = document.getElementById("lorebook-editor-error");
  expandAllBtn = document.getElementById("lorebook-expand-all");
  collapseAllBtn = document.getElementById("lorebook-collapse-all");
  addEntryBtn = document.getElementById("lorebook-add-entry");
  editorDownloadBtn = document.getElementById("lorebook-editor-download");
  scanSourcesEl = document.getElementById("lorebook-scan-sources");
  scanAgentEl = document.getElementById("lorebook-scan-agent");

  if (!listEl || !uploadBtn) return;

  uploadBtn.addEventListener("click", () => {
    void handleUpload();
  });
  createBtn?.addEventListener("click", () => {
    void handleCreate();
  });
  loadDemoBtn?.addEventListener("click", () => {
    void handleLoadDemo();
  });
  editorCloseBtn?.addEventListener("click", closeEditor);
  editorSaveBtn?.addEventListener("click", () => {
    void saveEditor();
  });
  expandAllBtn?.addEventListener("click", () => setAllEntriesExpanded(true));
  collapseAllBtn?.addEventListener("click", () => setAllEntriesExpanded(false));
  addEntryBtn?.addEventListener("click", () => addEntry());
  editorDownloadBtn?.addEventListener("click", () => {
    if (editingBookId) void handleDownload(editingBookId);
  });

  void refreshList();
  void refreshScanPanel();
}

export async function refreshLorebookScanPanel() {
  await refreshScanPanel();
}

async function refreshScanPanel() {
  if (!scanSourcesEl) return;
  try {
    const agentId = getActiveAgentId();
    const data = await getLorebookScanConfig(agentId);
    scanConfigState = { ...(data.config || {}) };
    if (scanAgentEl) {
      scanAgentEl.textContent = `Previews for active agent: ${data.agent_name || data.agent_id}`;
    }
    renderScanSources(data.sources || []);
  } catch (err) {
    if (scanAgentEl) scanAgentEl.textContent = String(err.message || err);
    scanSourcesEl.innerHTML = "";
  }
}

function renderScanSources(sources) {
  if (!scanSourcesEl) return;
  scanSourcesEl.innerHTML = "";
  for (const source of sources) {
    const item = document.createElement("li");
    item.className = "lorebook-scan-source";

    const label = document.createElement("label");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = source.enabled !== false;
    checkbox.addEventListener("change", () => {
      void updateScanSource(source.id, checkbox.checked, checkbox);
    });
    const title = document.createElement("span");
    title.textContent = source.label;
    label.appendChild(checkbox);
    label.appendChild(title);

    const preview = document.createElement("pre");
    preview.className = "lorebook-scan-source-preview";
    preview.textContent = source.preview || "(empty)";

    item.appendChild(label);
    item.appendChild(preview);
    scanSourcesEl.appendChild(item);
  }
}

async function updateScanSource(sourceId, enabled, checkbox) {
  const previous = { ...scanConfigState };
  scanConfigState[sourceId] = enabled;
  try {
    const data = await putLorebookScanConfig({ [sourceId]: enabled });
    scanConfigState = { ...(data.config || {}) };
    renderScanSources(data.sources || []);
    onLorebooksChanged();
  } catch (err) {
    scanConfigState = previous;
    if (checkbox) checkbox.checked = !enabled;
    showToast(String(err.message || err), true);
  }
}

export async function refreshLorebookList() {
  await refreshList();
}

async function refreshList() {
  try {
    const data = await getLorebooks();
    const books = data.lorebooks || [];
    listEl.innerHTML = "";
    if (books.length === 0) {
      listEl.classList.add("hidden");
      listEmptyEl?.classList.remove("hidden");
      return;
    }
    listEmptyEl?.classList.add("hidden");
    listEl.classList.remove("hidden");
    for (const book of books) {
      const item = document.createElement("li");
      item.className = "lorebooks-list-item";
      const meta = document.createElement("div");
      meta.className = "lorebooks-list-meta";
      meta.innerHTML = `<strong>${escapeHtml(book.name)}</strong> <span class="lorebooks-list-id">(${escapeHtml(book.id)})</span> — ${book.entry_count} entries`;
      const actions = document.createElement("div");
      actions.className = "lorebooks-list-actions";
      const editBtn = document.createElement("button");
      editBtn.type = "button";
      editBtn.textContent = "Edit";
      editBtn.addEventListener("click", () => {
        void openEditor(book.id);
      });
      const downloadBtn = document.createElement("button");
      downloadBtn.type = "button";
      downloadBtn.textContent = "Download";
      downloadBtn.addEventListener("click", () => {
        void handleDownload(book.id);
      });
      const removeBtn = document.createElement("button");
      removeBtn.type = "button";
      removeBtn.textContent = "Remove";
      removeBtn.className = "lorebooks-remove-btn";
      removeBtn.addEventListener("click", () => {
        void handleRemove(book.id, book.name);
      });
      actions.appendChild(editBtn);
      actions.appendChild(downloadBtn);
      actions.appendChild(removeBtn);
      item.appendChild(meta);
      item.appendChild(actions);
      listEl.appendChild(item);
    }
  } catch (err) {
    showToast(String(err.message || err), true);
  }
}

async function handleUpload() {
  const file = uploadInput?.files?.[0];
  if (!file) {
    showToast("Choose a .json lorebook file first.", true);
    return;
  }
  try {
    const result = await uploadLorebook(file);
    if (uploadInput) uploadInput.value = "";
    showToast(result.message || `Loaded ${result.lorebook_id}`);
    await refreshList();
    onLorebooksChanged();
    if (result.lorebook_id) {
      await openEditor(result.lorebook_id);
    }
  } catch (err) {
    showToast(String(err.message || err), true);
  }
}

async function handleCreate() {
  const name = window.prompt("Lorebook name:", "New lorebook");
  if (name === null) return;
  try {
    const result = await createLorebook({ name: name.trim() || "New lorebook" });
    showToast(result.message || `Created ${result.lorebook_id}`);
    await refreshList();
    onLorebooksChanged();
    if (result.lorebook_id) {
      await openEditor(result.lorebook_id);
    }
  } catch (err) {
    showToast(String(err.message || err), true);
  }
}

async function handleLoadDemo() {
  try {
    const result = await loadDemoLorebook();
    showToast(result.message || `Loaded ${result.lorebook_id}`);
    await refreshList();
    onLorebooksChanged();
    if (result.lorebook_id) {
      await openEditor(result.lorebook_id);
    }
  } catch (err) {
    showToast(String(err.message || err), true);
  }
}

async function handleRemove(bookId, name) {
  if (!window.confirm(`Remove lorebook "${name}" from this session?`)) return;
  try {
    await deleteLorebook(bookId);
    if (editingBookId === bookId) closeEditor();
    await refreshList();
    onLorebooksChanged();
    showToast(`Removed lorebook ${bookId}`);
  } catch (err) {
    showToast(String(err.message || err), true);
  }
}

async function handleDownload(bookId) {
  try {
    const { blob, filename } = await downloadLorebook(bookId);
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
    showToast(`Downloaded ${filename}`);
  } catch (err) {
    showToast(String(err.message || err), true);
  }
}

async function openEditor(bookId) {
  setEditorError("");
  try {
    const data = await getLorebook(bookId);
    editingBookId = bookId;
    editingBook = data.lorebook;
    editorTitle.textContent = `Edit — ${editingBook.name}`;
    renderEditorEntries();
    editorPanel?.classList.remove("hidden");
  } catch (err) {
    showToast(String(err.message || err), true);
  }
}

function closeEditor() {
  editingBookId = null;
  editingBook = null;
  editorPanel?.classList.add("hidden");
  if (editorEntries) editorEntries.innerHTML = "";
  setEditorError("");
}

function updateEditorStatus(saved = false) {
  if (!editorStatus || !editorEntries) return;
  const count = editorEntries.querySelectorAll(".lorebook-entry-card").length;
  if (saved) {
    editorStatus.textContent = `${count} ${count === 1 ? "entry" : "entries"} (sorted by order)`;
  } else {
    editorStatus.textContent = `${count} ${count === 1 ? "entry" : "entries"} (unsaved — click Save changes)`;
  }
}

function entryTitleText(entry) {
  const comment = (entry.comment || "").trim();
  return comment || `Entry ${entry.uid}`;
}

function syncEntryTitle(card) {
  const title = card.querySelector(".lorebook-entry-title");
  const commentInput = card.querySelector('input[data-field="comment"]');
  if (title && commentInput) {
    title.textContent = entryTitleText({ uid: card.dataset.uid, comment: commentInput.value });
  }
}

function nextEntryUid() {
  let max = 0;
  for (const entry of editingBook?.entries ?? []) {
    max = Math.max(max, Number(entry.uid) || 0);
  }
  for (const card of editorEntries?.querySelectorAll(".lorebook-entry-card") ?? []) {
    max = Math.max(max, Number.parseInt(card.dataset.uid, 10) || 0);
  }
  return max + 1;
}

function nextEntryOrder() {
  let max = -1;
  for (const entry of editingBook?.entries ?? []) {
    max = Math.max(max, Number(entry.order) || 0);
  }
  for (const card of editorEntries?.querySelectorAll(".lorebook-entry-card") ?? []) {
    max = Math.max(max, Number.parseInt(card.dataset.order ?? "0", 10) || 0);
  }
  return max + 1;
}

function addEntry() {
  if (!editorEntries) return;
  const entry = {
    uid: nextEntryUid(),
    enabled: true,
    constant: false,
    keys: [],
    keys_secondary: [],
    selective: false,
    selective_logic: 0,
    content: "",
    comment: "New entry",
    order: nextEntryOrder(),
    ignore_budget: false,
  };
  const card = buildEntryCard(entry);
  editorEntries.appendChild(card);
  setEntryExpanded(card, true);
  updateEditorStatus();
  card.scrollIntoView({ behavior: "smooth", block: "nearest" });
  card.querySelector('input[data-field="comment"]')?.focus();
}

function removeEntryCard(card) {
  const title = card.querySelector(".lorebook-entry-title")?.textContent?.trim() || "this entry";
  if (!window.confirm(`Delete "${title}" from this session's copy of the lorebook?`)) return;
  card.remove();
  updateEditorStatus();
}

function renderEditorEntries() {
  if (!editorEntries || !editingBook) return;
  editorEntries.innerHTML = "";
  const sorted = [...editingBook.entries].sort(
    (a, b) => (a.order ?? 0) - (b.order ?? 0) || (a.uid ?? 0) - (b.uid ?? 0),
  );
  for (const entry of sorted) {
    editorEntries.appendChild(buildEntryCard(entry));
  }
  updateEditorStatus(true);
}

function buildEntryCard(entry) {
  const card = document.createElement("article");
  card.className = "lorebook-entry-card collapsed";
  card.dataset.uid = String(entry.uid);
  card.dataset.order = String(entry.order ?? 0);

  const header = document.createElement("div");
  header.className = "lorebook-entry-header";

  const toggleBtn = document.createElement("button");
  toggleBtn.type = "button";
  toggleBtn.className = "lorebook-entry-toggle";
  toggleBtn.setAttribute("aria-expanded", "false");
  toggleBtn.setAttribute("aria-label", "Expand entry");
  toggleBtn.textContent = "▸";
  toggleBtn.addEventListener("click", (event) => {
    event.stopPropagation();
    setEntryExpanded(card, card.classList.contains("collapsed"));
  });

  const enableLabel = document.createElement("label");
  enableLabel.className = "lorebook-entry-check";
  const enableInput = document.createElement("input");
  enableInput.type = "checkbox";
  enableInput.checked = entry.enabled !== false;
  enableInput.dataset.field = "enabled";
  enableInput.addEventListener("change", () => updateEditorStatus());
  enableLabel.appendChild(enableInput);
  enableLabel.append(" Enabled");
  const constantLabel = document.createElement("label");
  constantLabel.className = "lorebook-entry-check";
  const constantInput = document.createElement("input");
  constantInput.type = "checkbox";
  constantInput.checked = !!entry.constant;
  constantInput.dataset.field = "constant";
  constantInput.addEventListener("change", () => updateEditorStatus());
  constantLabel.appendChild(constantInput);
  constantLabel.append(" Constant");
  const title = document.createElement("span");
  title.className = "lorebook-entry-title";
  title.textContent = entryTitleText(entry);
  title.addEventListener("click", () => {
    setEntryExpanded(card, card.classList.contains("collapsed"));
  });

  const deleteBtn = document.createElement("button");
  deleteBtn.type = "button";
  deleteBtn.className = "lorebook-entry-delete-btn";
  deleteBtn.textContent = "Delete";
  deleteBtn.addEventListener("click", (event) => {
    event.stopPropagation();
    removeEntryCard(card);
  });

  header.appendChild(toggleBtn);
  header.appendChild(enableLabel);
  header.appendChild(constantLabel);
  header.appendChild(title);
  header.appendChild(deleteBtn);

  const body = document.createElement("div");
  body.className = "lorebook-entry-body";

  const commentLabel = document.createElement("label");
  commentLabel.className = "lorebook-entry-field";
  commentLabel.innerHTML = "<span>Label</span>";
  const commentInput = document.createElement("input");
  commentInput.type = "text";
  commentInput.value = entry.comment || "";
  commentInput.dataset.field = "comment";
  commentInput.placeholder = `Entry ${entry.uid}`;
  commentInput.addEventListener("input", () => {
    syncEntryTitle(card);
    updateEditorStatus();
  });
  commentLabel.appendChild(commentInput);

  const keysLabel = document.createElement("label");
  keysLabel.className = "lorebook-entry-field";
  keysLabel.innerHTML = "<span>Keys (comma-separated)</span>";
  const keysInput = document.createElement("input");
  keysInput.type = "text";
  keysInput.value = (entry.keys || []).join(", ");
  keysInput.dataset.field = "keys";
  keysInput.addEventListener("input", () => updateEditorStatus());
  keysLabel.appendChild(keysInput);

  const contentLabel = document.createElement("label");
  contentLabel.className = "lorebook-entry-field";
  contentLabel.innerHTML = "<span>Content</span>";
  const contentArea = document.createElement("textarea");
  contentArea.rows = 4;
  contentArea.value = entry.content || "";
  contentArea.dataset.field = "content";
  contentArea.addEventListener("input", () => updateEditorStatus());
  contentLabel.appendChild(contentArea);

  body.appendChild(commentLabel);
  body.appendChild(keysLabel);
  body.appendChild(contentLabel);

  card.appendChild(header);
  card.appendChild(body);
  return card;
}

function setEntryExpanded(card, expanded) {
  const toggleBtn = card.querySelector(".lorebook-entry-toggle");
  card.classList.toggle("collapsed", !expanded);
  if (toggleBtn) {
    toggleBtn.setAttribute("aria-expanded", expanded ? "true" : "false");
    toggleBtn.setAttribute("aria-label", expanded ? "Collapse entry" : "Expand entry");
    toggleBtn.textContent = expanded ? "▾" : "▸";
  }
}

function setAllEntriesExpanded(expanded) {
  if (!editorEntries) return;
  for (const card of editorEntries.querySelectorAll(".lorebook-entry-card")) {
    setEntryExpanded(card, expanded);
  }
}

function collectEntryFromCard(card, base) {
  const enabled = card.querySelector('input[data-field="enabled"]');
  const constant = card.querySelector('input[data-field="constant"]');
  const comment = card.querySelector('input[data-field="comment"]');
  const keys = card.querySelector('input[data-field="keys"]');
  const content = card.querySelector('textarea[data-field="content"]');
  const uid = Number.parseInt(card.dataset.uid, 10);
  const order = Number.parseInt(card.dataset.order ?? String(base?.order ?? 0), 10);
  return {
    uid,
    enabled: enabled?.checked ?? true,
    constant: constant?.checked ?? false,
    keys: splitKeys(keys?.value || ""),
    keys_secondary: base?.keys_secondary ?? [],
    selective: base?.selective ?? false,
    selective_logic: base?.selective_logic ?? 0,
    content: content?.value ?? "",
    comment: comment?.value ?? "",
    order: Number.isFinite(order) ? order : 0,
    ignore_budget: base?.ignore_budget ?? false,
  };
}

function collectEntriesFromEditor() {
  if (!editorEntries || !editingBook) return [];
  const byUid = new Map(editingBook.entries.map((e) => [String(e.uid), { ...e }]));
  const entries = [];
  for (const card of editorEntries.querySelectorAll(".lorebook-entry-card")) {
    const base = byUid.get(card.dataset.uid) ?? null;
    entries.push(collectEntryFromCard(card, base));
  }
  return entries;
}

function splitKeys(text) {
  return text
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean);
}

async function saveEditor() {
  if (!editingBookId || !editingBook) return;
  setEditorError("");
  try {
    const entries = collectEntriesFromEditor();
    const payload = {
      name: editingBook.name,
      entries,
    };
    const data = await putLorebook(editingBookId, payload);
    editingBook = data.lorebook;
    renderEditorEntries();
    updateEditorStatus(true);
    showToast("Lorebook saved.");
    onLorebooksChanged();
    await refreshList();
  } catch (err) {
    setEditorError(String(err.message || err));
  }
}

function setEditorError(message) {
  if (editorError) editorError.textContent = message || "";
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export function initAppTabs() {
  const tabMain = document.getElementById("tab-main");
  const tabLorebooks = document.getElementById("tab-lorebooks");
  const panelMain = document.getElementById("main-tab-panel");
  const panelLorebooks = document.getElementById("lorebooks-tab-panel");
  if (!tabMain || !tabLorebooks || !panelMain || !panelLorebooks) return;

  function showTab(which) {
    const mainActive = which === "main";
    tabMain.classList.toggle("active", mainActive);
    tabLorebooks.classList.toggle("active", !mainActive);
    tabMain.setAttribute("aria-selected", mainActive ? "true" : "false");
    tabLorebooks.setAttribute("aria-selected", mainActive ? "false" : "true");
    panelMain.classList.toggle("hidden", !mainActive);
    panelLorebooks.classList.toggle("hidden", mainActive);
  }

  tabMain.addEventListener("click", () => showTab("main"));
  tabLorebooks.addEventListener("click", () => {
    showTab("lorebooks");
    void refreshList();
    void refreshScanPanel();
  });
}
