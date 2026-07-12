/** Entity templates tab — library on disk under entity_templates/ (1.2.2). */

import {
  deleteEntityTemplate,
  downloadEntityTemplateFile,
  fetchEntityTemplates,
  importEntityTemplate,
} from "./api.js";
import { registerTabShowHandler } from "./tabs.js";

let showToast = () => {};

let listEl;
let listEmptyEl;
let uploadInput;
let uploadBtn;

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

  if (!listEl || !uploadBtn) return;

  uploadBtn.addEventListener("click", () => uploadInput?.click());
  uploadInput?.addEventListener("change", () => {
    void handleUpload();
  });

  registerTabShowHandler("templates", refreshList);
  void refreshList();
}

export async function refreshTemplatesList() {
  await refreshList();
}

async function refreshList() {
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
      const li = document.createElement("li");
      li.className = "templates-list-item";

      const meta = document.createElement("div");
      meta.className = "templates-list-meta";
      const memoryNote = item.include_memory ? " · includes memory" : "";
      meta.innerHTML = `<strong>${escapeHtml(item.name)}</strong> <span class="templates-list-id">(${escapeHtml(item.kind)})</span> — ${escapeHtml(item.filename)}${memoryNote}`;

      const actions = document.createElement("div");
      actions.className = "templates-list-actions";

      const downloadBtn = document.createElement("button");
      downloadBtn.type = "button";
      downloadBtn.textContent = "Download";
      downloadBtn.addEventListener("click", () => {
        void handleDownload(item.id, item.filename);
      });

      const removeBtn = document.createElement("button");
      removeBtn.type = "button";
      removeBtn.textContent = "Remove";
      removeBtn.className = "templates-remove-btn";
      removeBtn.addEventListener("click", () => {
        void handleRemove(item.id, item.name);
      });

      actions.appendChild(downloadBtn);
      actions.appendChild(removeBtn);
      li.appendChild(meta);
      li.appendChild(actions);
      listEl.appendChild(li);
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

async function handleDownload(templateId, fallbackFilename) {
  try {
    const { filename } = await downloadEntityTemplateFile(templateId);
    showToast(`Downloaded ${filename || fallbackFilename}`, false);
  } catch (err) {
    showToast(String(err.message || err), true);
  }
}

async function handleRemove(templateId, name) {
  const label = String(name || templateId);
  if (!window.confirm(`Remove template "${label}" from the library?`)) return;
  try {
    const result = await deleteEntityTemplate(templateId);
    showToast(result.message || "Template removed.", false);
    await refreshList();
  } catch (err) {
    showToast(String(err.message || err), true);
  }
}

async function handleUpload() {
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
    await refreshList();
  } catch (err) {
    showToast(String(err.message || err) || "Invalid JSON file.", true);
  }
}
