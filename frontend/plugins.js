/** Plugins tab — catalog, enable/disable, generic panel renderer. */

import {
  fetchPlugins,
  enablePlugin,
  disablePlugin,
  fetchPluginPanel,
  postPluginAction,
  uploadPlugin,
} from "./api.js";
import { registerTabShowHandler } from "./tabs.js";

let showToastFn = () => {};
let onPluginsChangedFn = async () => {};
let selectedPluginId = null;

export function initPlugins({ showToastFn: toast, onPluginsChangedFn }) {
  showToastFn = toast || showToastFn;
  onPluginsChangedFn = onPluginsChangedFn || onPluginsChangedFn;

  const uploadBtn = document.getElementById("plugin-upload-btn");
  const uploadInput = document.getElementById("plugin-upload-input");
  if (uploadBtn && uploadInput) {
    uploadBtn.addEventListener("click", () => uploadInput.click());
    uploadInput.addEventListener("change", async () => {
      const file = uploadInput.files?.[0];
      uploadInput.value = "";
      if (!file) return;
      try {
        const data = await uploadPlugin(file);
        showToastFn(data.message || "Plugin uploaded.");
        await refreshPluginsList();
      } catch (err) {
        showToastFn(err.message || "Upload failed.");
      }
    });
  }

  registerTabShowHandler("plugins", refreshPluginsList);
}

export async function refreshPluginsList() {
  const listEl = document.getElementById("plugins-list");
  const emptyEl = document.getElementById("plugins-list-empty");
  const panelHost = document.getElementById("plugin-panel-host");
  if (!listEl) return;

  let data;
  try {
    data = await fetchPlugins();
  } catch (err) {
    if (emptyEl) {
      emptyEl.textContent = err.message || "Could not load plugins.";
      emptyEl.classList.remove("hidden");
    }
    listEl.classList.add("hidden");
    return;
  }

  const plugins = data.plugins || [];
  listEl.innerHTML = "";
  if (!plugins.length) {
    if (emptyEl) {
      emptyEl.textContent = "No plugins installed. Add a package under plugins/ or upload one.";
      emptyEl.classList.remove("hidden");
    }
    listEl.classList.add("hidden");
    if (panelHost) panelHost.innerHTML = "";
    return;
  }

  if (emptyEl) emptyEl.classList.add("hidden");
  listEl.classList.remove("hidden");

  for (const plugin of plugins) {
    const li = document.createElement("li");
    li.className = "plugins-list-item";
    const title = document.createElement("div");
    title.className = "plugins-list-title";
    title.textContent = plugin.label || plugin.id;
    const meta = document.createElement("div");
    meta.className = "plugins-list-meta";
    meta.textContent = plugin.description || plugin.id;
    const actions = document.createElement("div");
    actions.className = "plugins-list-actions";
    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = plugin.enabled ? "modal-cancel" : "settings-action-btn";
    toggle.textContent = plugin.enabled ? "Disable" : "Enable";
    toggle.addEventListener("click", async (ev) => {
      ev.stopPropagation();
      try {
        const result = plugin.enabled
          ? await disablePlugin(plugin.id)
          : await enablePlugin(plugin.id);
        showToastFn(result.message || "Updated.");
        await onPluginsChangedFn(result.snapshot);
        await refreshPluginsList();
        if (selectedPluginId === plugin.id) {
          await renderPluginPanel(plugin.id);
        }
      } catch (err) {
        showToastFn(err.message || "Update failed.");
      }
    });
    actions.appendChild(toggle);
    li.appendChild(title);
    li.appendChild(meta);
    li.appendChild(actions);
    li.addEventListener("click", () => {
      selectedPluginId = plugin.id;
      for (const item of listEl.querySelectorAll(".plugins-list-item")) {
        item.classList.toggle("selected", item === li);
      }
      void renderPluginPanel(plugin.id);
    });
    listEl.appendChild(li);
  }

  if (!selectedPluginId && plugins[0]) {
    selectedPluginId = plugins[0].id;
    const first = listEl.querySelector(".plugins-list-item");
    if (first) first.classList.add("selected");
    await renderPluginPanel(selectedPluginId);
  }
}

async function renderPluginPanel(pluginId) {
  const host = document.getElementById("plugin-panel-host");
  if (!host) return;
  host.innerHTML = "";
  let data;
  try {
    data = await fetchPluginPanel(pluginId);
  } catch (err) {
    host.textContent = err.message || "Could not load panel.";
    return;
  }
  const panel = data.panel || {};
  const heading = document.createElement("h3");
  heading.className = "plugins-panel-title";
  heading.textContent = panel.title || pluginId;
  host.appendChild(heading);
  if (panel.description) {
    const desc = document.createElement("p");
    desc.className = "plugins-panel-desc";
    desc.textContent = panel.description;
    host.appendChild(desc);
  }
  for (const section of panel.sections || []) {
    host.appendChild(renderPanelSection(pluginId, section));
  }
}

function renderPanelSection(pluginId, section) {
  const wrap = document.createElement("div");
  wrap.className = "plugins-panel-section";
  if (section.type === "text") {
    const p = document.createElement("p");
    p.className = "plugins-panel-text";
    p.textContent = section.content || "";
    wrap.appendChild(p);
    return wrap;
  }
  if (section.type === "key_value_list") {
    const ul = document.createElement("ul");
    ul.className = "plugins-kv-list";
    for (const item of section.items || []) {
      const li = document.createElement("li");
      li.textContent = `${item.key}: ${item.value}`;
      ul.appendChild(li);
    }
    wrap.appendChild(ul);
    return wrap;
  }
  if (section.type === "button") {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "settings-action-btn";
    btn.textContent = section.label || section.id || "Run";
    btn.addEventListener("click", async () => {
      try {
        const result = await postPluginAction(pluginId, section.id, section.params || {});
        showToastFn(result.message || "Done.");
        await renderPluginPanel(pluginId);
      } catch (err) {
        showToastFn(err.message || "Action failed.");
      }
    });
    wrap.appendChild(btn);
    return wrap;
  }
  return wrap;
}
