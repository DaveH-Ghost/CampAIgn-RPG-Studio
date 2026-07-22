/** Plugins tab — catalog, enable/disable, generic panel renderer. */

import {
  disablePlugin,
  enablePlugin,
  fetchEntityTemplates,
  fetchPluginPanel,
  fetchPlugins,
  postPluginAction,
  uploadPlugin,
} from "./api.js";
import { registerTabShowHandler } from "./tabs.js";

let showToastFn = () => {};
let onPluginsChangedFn = async () => {};
let selectedPluginId = null;

export function initPlugins({ showToastFn: toast, onPluginsChangedFn: onChanged }) {
  showToastFn = toast || showToastFn;
  onPluginsChangedFn = onChanged || onPluginsChangedFn;

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
    meta.textContent = plugin.enabled ? "Enabled" : "Disabled";
    const actions = document.createElement("div");
    actions.className = "plugins-list-actions";
    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "settings-action-btn";
    toggle.textContent = plugin.enabled ? "Disable" : "Enable";
    toggle.addEventListener("click", async (event) => {
      event.stopPropagation();
      try {
        if (plugin.enabled) {
          await disablePlugin(plugin.id);
          showToastFn(`Disabled ${plugin.label || plugin.id}.`);
        } else {
          await enablePlugin(plugin.id);
          showToastFn(`Enabled ${plugin.label || plugin.id}.`);
        }
        await onPluginsChangedFn();
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
    host.appendChild(await renderPanelSection(pluginId, section));
  }
}

function collectParamsFromInputs(host, mapping) {
  const params = {};
  for (const [paramName, inputId] of Object.entries(mapping || {})) {
    const el = host.querySelector(`[data-panel-input="${inputId}"]`);
    if (!el) continue;
    params[paramName] = el.value;
  }
  return params;
}

function renderInlinePanelInput(field) {
  const label = document.createElement("label");
  label.className = "plugins-panel-field";
  const span = document.createElement("span");
  span.textContent = field.label || field.id || "Value";
  label.appendChild(span);
  const input = document.createElement("input");
  input.type = field.type === "text" ? "text" : "number";
  input.value = field.value ?? "";
  if (field.min != null) input.min = String(field.min);
  if (field.max != null) input.max = String(field.max);
  input.dataset.panelInput = field.id || "input";
  label.appendChild(input);
  return label;
}

async function renderPanelSection(pluginId, section) {
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
  if (section.type === "number_input") {
    wrap.appendChild(
      renderInlinePanelInput({
        id: section.id || "number_input",
        type: "number",
        label: section.label || section.id || "Value",
        value: section.value ?? "",
        min: section.min,
        max: section.max,
      }),
    );
    return wrap;
  }
  if (section.type === "template_id") {
    const label = document.createElement("label");
    label.className = "plugins-panel-field";
    const span = document.createElement("span");
    span.textContent = section.label || "Template";
    label.appendChild(span);
    const select = document.createElement("select");
    select.dataset.panelInput = section.id || "template_id";
    const blank = document.createElement("option");
    blank.value = "";
    blank.textContent = "(select template)";
    select.appendChild(blank);
    try {
      const data = await fetchEntityTemplates();
      const kindFilter = section.kind || null;
      for (const tpl of data.templates || []) {
        if (kindFilter && tpl.kind && tpl.kind !== kindFilter) continue;
        const opt = document.createElement("option");
        opt.value = tpl.id;
        opt.textContent = tpl.name ? `${tpl.name} (${tpl.id})` : tpl.id;
        select.appendChild(opt);
      }
    } catch {
      // leave empty beyond blank option
    }
    label.appendChild(select);
    wrap.appendChild(label);
    return wrap;
  }
  if (section.type === "button") {
    for (const field of section.inputs || []) {
      wrap.appendChild(renderInlinePanelInput(field));
    }
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "settings-action-btn";
    btn.textContent = section.label || section.id || "Run";
    btn.addEventListener("click", async () => {
      try {
        const host = document.getElementById("plugin-panel-host");
        const fromInputs = collectParamsFromInputs(host, section.params_from_inputs || {});
        const params = { ...(section.params || {}), ...fromInputs };
        const result = await postPluginAction(pluginId, section.id, params);
        showToastFn(result.message || "Done.");
        if (result.snapshot) {
          await onPluginsChangedFn(result.snapshot);
        }
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
