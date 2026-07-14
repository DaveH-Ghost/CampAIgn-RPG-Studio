/**
 * Generic handler param_fields rendering and CLI emission (Studio 1.4.2).
 */

import { cliQuote } from "./api.js";

/** @param {Record<string, object>} catalogById */
export function formatHandlerSummaryFromCatalog(action, catalogById) {
  const handlerId = action?.handler_id;
  if (!handlerId) return "no handler";
  const params = action?.handler_params || {};
  const entry = catalogById?.[handlerId];
  const template = entry?.summary_template || "";
  let text = template
    ? template.replace(/\{([^{}]+)\}/g, (_, key) => {
        const value = params[key];
        return value == null || value === "" ? "?" : String(value);
      })
    : handlerId;
  const fields = entry?.param_fields || [];
  for (const field of fields) {
    if (field.type !== "handler_ref") continue;
    const refId = String(params[field.name] || "").trim();
    if (!refId || refId === "none") continue;
    const short = field.summary_key || field.name;
    text += `; ${short} ${refId}`;
  }
  return text;
}

/**
 * @param {HTMLElement} host
 * @param {object[]} fields
 * @param {{
 *   params: Record<string, string>,
 *   areas: string[],
 *   catalogById: Record<string, object>,
 *   namePrefix?: string,
 *   parentHandlerId?: string,
 *   onChange?: () => void,
 *   attachTemplateHelp?: (labelEl: HTMLElement) => void,
 * }} ctx
 */
export function renderParamFields(host, fields, ctx) {
  const {
    params,
    areas,
    catalogById,
    namePrefix = "",
    onChange,
    attachTemplateHelp,
  } = ctx;
  for (const field of fields || []) {
    const type = field.type || "text";
    if (type === "handler_ref") {
      renderHandlerRefField(host, field, ctx);
      continue;
    }
    const wrap = document.createElement("label");
    wrap.className = "modal-field";
    const label = document.createElement("span");
    label.className = "modal-field-label-row";
    label.textContent = field.label || field.name;
    if (field.template_vars && attachTemplateHelp) {
      attachTemplateHelp(label);
    }
    wrap.appendChild(label);

    const paramName = namePrefix + field.name;
    let input;
    if (type === "textarea") {
      input = document.createElement("textarea");
      input.rows = 2;
      input.value = params[paramName] ?? field.default ?? "";
    } else if (type === "select") {
      input = document.createElement("select");
      for (const opt of field.options || []) {
        const o = document.createElement("option");
        const value = typeof opt === "string" ? opt : opt.value;
        const lab = typeof opt === "string" ? opt : opt.label || opt.value;
        o.value = value;
        o.textContent = lab;
        if (String(params[paramName] ?? field.default ?? "") === String(value)) {
          o.selected = true;
        }
        input.appendChild(o);
      }
    } else if (type === "area_id") {
      input = document.createElement("select");
      const current = params[paramName] ?? field.default ?? areas[0] ?? "";
      for (const areaId of areas) {
        const o = document.createElement("option");
        o.value = areaId;
        o.textContent = areaId;
        if (areaId === current) o.selected = true;
        input.appendChild(o);
      }
    } else if (type === "coord") {
      const row = document.createElement("div");
      row.className = "action-dest-row";
      const raw = String(params[paramName] ?? field.default ?? "0,0");
      const [x0, y0] = raw.split(",");
      for (const [suffix, val, lab] of [
        ["_x", (x0 || "0").trim(), "X"],
        ["_y", (y0 || "0").trim(), "Y"],
      ]) {
        const cell = document.createElement("label");
        cell.className = "modal-field action-dest-coord";
        const span = document.createElement("span");
        span.textContent = lab;
        cell.appendChild(span);
        const num = document.createElement("input");
        num.type = "number";
        num.name = `${paramName}${suffix}`;
        num.value = val;
        if (onChange) num.addEventListener("change", onChange);
        cell.appendChild(num);
        row.appendChild(cell);
      }
      wrap.appendChild(row);
      host.appendChild(wrap);
      continue;
    } else {
      input = document.createElement("input");
      input.type = type === "number" ? "number" : "text";
      input.value = params[paramName] ?? field.default ?? "";
    }
    input.name = paramName;
    if (field.placeholder) input.placeholder = field.placeholder;
    if (field.required) input.required = true;
    if (onChange) input.addEventListener("change", onChange);
    wrap.appendChild(input);
    host.appendChild(wrap);
  }
}

function renderHandlerRefField(host, field, ctx) {
  const { params, catalogById, namePrefix = "", onChange, areas, attachTemplateHelp } =
    ctx;
  const paramName = namePrefix + field.name;
  const prefix = field.param_prefix || "";
  const exclude = new Set(field.exclude_handlers || []);
  if (field.exclude_self && ctx.parentHandlerId) {
    exclude.add(ctx.parentHandlerId);
  }

  const wrap = document.createElement("div");
  wrap.className = "action-followup-fields";

  const labelWrap = document.createElement("label");
  labelWrap.className = "modal-field";
  const label = document.createElement("span");
  label.textContent = field.label || field.name;
  labelWrap.appendChild(label);
  const select = document.createElement("select");
  select.name = paramName;
  const none = document.createElement("option");
  none.value = "none";
  none.textContent = "None";
  select.appendChild(none);
  const current = String(params[paramName] || "none");
  for (const id of Object.keys(catalogById || {}).sort()) {
    if (exclude.has(id)) continue;
    const entry = catalogById[id];
    const opt = document.createElement("option");
    opt.value = id;
    opt.textContent = entry.description ? `${id} — ${entry.description}` : id;
    if (id === current) opt.selected = true;
    select.appendChild(opt);
  }
  if (current !== "none" && ![...select.options].some((o) => o.value === current)) {
    const opt = document.createElement("option");
    opt.value = current;
    opt.textContent = current;
    opt.selected = true;
    select.appendChild(opt);
  }
  labelWrap.appendChild(select);
  wrap.appendChild(labelWrap);

  const nestedHost = document.createElement("div");
  nestedHost.className = "action-followup-nested";
  wrap.appendChild(nestedHost);

  const syncNested = () => {
    nestedHost.innerHTML = "";
    const refId = select.value;
    if (!refId || refId === "none") return;
    const entry = catalogById[refId];
    const nestedFields = entry?.param_fields || [];
    if (!nestedFields.length) return;
    renderParamFields(nestedHost, nestedFields, {
      params,
      areas,
      catalogById,
      namePrefix: prefix,
      onChange,
      attachTemplateHelp,
      parentHandlerId: refId,
    });
  };
  select.addEventListener("change", () => {
    syncNested();
    if (onChange) onChange();
  });
  syncNested();
  host.appendChild(wrap);
}

/**
 * @param {HTMLFormElement} form
 * @param {object[]} fields
 * @param {Record<string, object>} catalogById
 * @param {string} [namePrefix]
 */
export function collectHandlerParams(form, fields, catalogById, namePrefix = "") {
  /** @type {Record<string, string>} */
  const out = {};
  for (const field of fields || []) {
    const type = field.type || "text";
    const paramName = namePrefix + field.name;
    if (type === "coord") {
      const x = form.elements[`${paramName}_x`]?.value?.trim() ?? "0";
      const y = form.elements[`${paramName}_y`]?.value?.trim() ?? "0";
      out[paramName] = `${x},${y}`;
      continue;
    }
    if (type === "handler_ref") {
      const refId = form.elements[paramName]?.value?.trim() || "none";
      if (!refId || refId === "none") continue;
      out[paramName] = refId;
      const prefix = field.param_prefix || "";
      const nestedFields = catalogById[refId]?.param_fields || [];
      Object.assign(out, collectHandlerParams(form, nestedFields, catalogById, prefix));
      continue;
    }
    const el = form.elements[paramName];
    if (!el) continue;
    const value = String(el.value ?? "").trim();
    if (value !== "") out[paramName] = value;
  }
  return out;
}

/** Emit CLI tokens for handler params (already validated by engine). */
export function handlerParamsToCliParts(params) {
  const parts = [];
  for (const [key, value] of Object.entries(params || {})) {
    if (value == null || String(value).trim() === "") continue;
    parts.push(key, cliQuote(String(value)));
  }
  return parts;
}
