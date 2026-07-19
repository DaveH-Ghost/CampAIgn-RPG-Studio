/** Entity and area template tabs (1.2.2 / 1.3.1). */

import {
  deleteAreaTemplate,
  deleteEntityTemplate,
  downloadAreaTemplateFile,
  downloadEntityTemplateFile,
  fetchAreaTemplates,
  fetchEntityTemplates,
  importAreaTemplate,
  importEntityTemplate,
} from "./api.js";
import { registerTabShowHandler } from "./tabs.js";
import { openLoadAreaTemplateModal, openSaveAreaTemplateModal } from "./ui.js";

let showToast = () => {};

let listEl;
let listEmptyEl;
let uploadInput;
let uploadBtn;
let areaListEl;
let areaListEmptyEl;
let areaUploadInput;
let areaUploadBtn;
let areaSaveBtn;

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export function initTemplates({ showToastFn }) {
  showToast = showToastFn ?? showToast;

  listEl = document.getElementById("templates-list");
  listEmptyEl = document.getElementById("templates-list-empty");
  uploadInput = document.getElementById("template-upload-input");
  uploadBtn = document.getElementById("template-upload-btn");
  areaListEl = document.getElementById("area-templates-list");
  areaListEmptyEl = document.getElementById("area-templates-list-empty");
  areaUploadInput = document.getElementById("area-template-upload-input");
  areaUploadBtn = document.getElementById("area-template-upload-btn");
  areaSaveBtn = document.getElementById("area-template-save-btn");

  if (!listEl || !uploadBtn) return;

  uploadBtn.addEventListener("click", () => uploadInput?.click());
  uploadInput?.addEventListener("change", () => {
    void handleEntityUpload();
  });
  areaUploadBtn?.addEventListener("click", () => areaUploadInput?.click());
  areaUploadInput?.addEventListener("change", () => {
    void handleAreaUpload();
  });
  areaSaveBtn?.addEventListener("click", () => {
    void openSaveAreaTemplateModal();
  });

  registerTabShowHandler("templates", refreshAllLists);
  void refreshAllLists();
}

export async function refreshTemplatesList() {
  await refreshAllLists();
}

async function refreshAllLists() {
  await Promise.all([refreshEntityList(), refreshAreaList()]);
}

async function refreshEntityList() {
  if (!listEl) return;
  try {
    const data = await fetchEntityTemplates();
    const templates = data.templates || [];
    listEl.innerHTML = "";
    if (!templates.length) {
      listEl.classList.add("hidden");
      if (listEmptyEl) {
        listEmptyEl.textContent = "No templates saved yet.";
        listEmptyEl.classList.remove("hidden");
      }
      return;
    }
    if (listEmptyEl) listEmptyEl.classList.add("hidden");
    listEl.classList.remove("hidden");

    for (const item of templates) {
      listEl.appendChild(
        renderTemplateRow(item, {
          onDownload: () => handleEntityDownload(item.id, item.filename),
          onRemove: () => handleEntityRemove(item.id, item.name),
          metaText: `${escapeHtml(item.filename)}${item.include_memory ? " · includes memory" : ""}`,
        }),
      );
    }
  } catch (err) {
    listEl.innerHTML = "";
    listEl.classList.add("hidden");
    if (listEmptyEl) {
      listEmptyEl.textContent = String(err.message || err);
      listEmptyEl.classList.remove("hidden");
    }
  }
}

async function refreshAreaList() {
  if (!areaListEl) return;
  try {
    const data = await fetchAreaTemplates();
    const templates = data.templates || [];
    areaListEl.innerHTML = "";
    if (!templates.length) {
      areaListEl.classList.add("hidden");
      if (areaListEmptyEl) {
        areaListEmptyEl.textContent = "No area templates saved yet.";
        areaListEmptyEl.classList.remove("hidden");
      }
      return;
    }
    if (areaListEmptyEl) areaListEmptyEl.classList.add("hidden");
    areaListEl.classList.remove("hidden");

    for (const item of templates) {
      const size =
        item.grid_width && item.grid_height ? `${item.grid_width}×${item.grid_height}` : "area";
      const counts = `${item.object_count ?? 0} obj · ${item.decoration_count ?? 0} decor`;
      areaListEl.appendChild(
        renderTemplateRow(item, {
          onDownload: () => handleAreaDownload(item.id, item.filename),
          onRemove: () => handleAreaRemove(item.id, item.name),
          metaText: `${escapeHtml(item.filename)} · ${size} · ${counts}`,
        }),
      );
    }
  } catch (err) {
    areaListEl.innerHTML = "";
    areaListEl.classList.add("hidden");
    if (areaListEmptyEl) {
      areaListEmptyEl.textContent = String(err.message || err);
      areaListEmptyEl.classList.remove("hidden");
    }
  }
}

function renderTemplateRow(item, { onDownload, onRemove, metaText }) {
  const li = document.createElement("li");
  li.className = "templates-list-item";

  const meta = document.createElement("div");
  meta.className = "templates-list-meta";
  meta.innerHTML = `<strong>${escapeHtml(item.name)}</strong> <span class="templates-list-id">(${escapeHtml(item.kind)})</span> — ${metaText}`;

  const actions = document.createElement("div");
  actions.className = "templates-list-actions";

  const downloadBtn = document.createElement("button");
  downloadBtn.type = "button";
  downloadBtn.textContent = "Download";
  downloadBtn.addEventListener("click", () => {
    void onDownload();
  });

  const removeBtn = document.createElement("button");
  removeBtn.type = "button";
  removeBtn.textContent = "Remove";
  removeBtn.className = "templates-remove-btn";
  removeBtn.addEventListener("click", () => {
    void onRemove();
  });

  actions.appendChild(downloadBtn);
  actions.appendChild(removeBtn);
  li.appendChild(meta);
  li.appendChild(actions);
  return li;
}

async function handleEntityDownload(templateId, fallbackFilename) {
  try {
    const { filename } = await downloadEntityTemplateFile(templateId);
    showToast(`Downloaded ${filename || fallbackFilename}`, false);
  } catch (err) {
    showToast(String(err.message || err), true);
  }
}

async function handleEntityRemove(templateId, name) {
  const label = String(name || templateId);
  if (!window.confirm(`Remove template "${label}" from the library?`)) return;
  try {
    const result = await deleteEntityTemplate(templateId);
    showToast(result.message || "Template removed.", false);
    await refreshEntityList();
  } catch (err) {
    showToast(String(err.message || err), true);
  }
}

async function handleAreaDownload(templateId, fallbackFilename) {
  try {
    const { filename } = await downloadAreaTemplateFile(templateId);
    showToast(`Downloaded ${filename || fallbackFilename}`, false);
  } catch (err) {
    showToast(String(err.message || err), true);
  }
}

async function handleAreaRemove(templateId, name) {
  const label = String(name || templateId);
  if (!window.confirm(`Remove area template "${label}" from the library?`)) return;
  try {
    const result = await deleteAreaTemplate(templateId);
    showToast(result.message || "Template removed.", false);
    await refreshAreaList();
  } catch (err) {
    showToast(String(err.message || err), true);
  }
}

async function handleEntityUpload() {
  const file = uploadInput?.files?.[0];
  if (uploadInput) uploadInput.value = "";
  if (!file) return;

  try {
    const text = await file.text();
    const template = JSON.parse(text);
    const result = await importEntityTemplate({
      filename: file.name,
      template,
    });
    showToast(result.message || "Template imported.", false);
    await refreshEntityList();
  } catch (err) {
    showToast(String(err.message || err) || "Invalid JSON file.", true);
  }
}

async function handleAreaUpload() {
  const file = areaUploadInput?.files?.[0];
  if (areaUploadInput) areaUploadInput.value = "";
  if (!file) return;

  try {
    const text = await file.text();
    const template = JSON.parse(text);
    const result = await importAreaTemplate({
      filename: file.name,
      template,
    });
    showToast(result.message || "Area template imported.", false);
    await refreshAreaList();
  } catch (err) {
    showToast(String(err.message || err) || "Invalid JSON file.", true);
  }
}
