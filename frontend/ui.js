/**
 * Context menu, modals, toast (V0.3.1c).
 */

import {
  buildCompoundTurnPayload,
  buildCreateAgent,
  buildCreateHiddenTrigger,
  buildCreateObject,
  buildEditAgent,
  buildEditObject,
  createPlayerSeat,
  downloadAreaTemplateFromArea,
  downloadEntityTemplateFromEntity,
  fetchAreaTemplates,
  fetchEntityTemplates,
  getMemoryModules,
  getPrompt,
  getState,
  memoryOptionFieldName,
  parseCreatedAgentId,
  parseCreatedObjectId,
  postActiveAgent,
  postActiveArea,
  postCommand,
  postCreateArea,
  postDeleteArea,
  postEditArea,
  postEntityPrivateData,
  postEvent,
  postMergeEntityFormPrivateData,
  postSaveAreaTemplate,
  fetchEntityFormSections,
  postSaveEntityTemplate,
  postSpawnAreaFromTemplate,
  postSpawnAreaTemplate,
  postSpawnEntityFromTemplate,
  postSpawnEntityTemplate,
} from "./api.js";
import { isSceneEditMode } from "./decorations.js";
import { CELL_SIZE } from "./gridViewport.js";
import { initObjectActions, openManageObjectActionsModal } from "./objectActions.js";
import { loadPlayerTurnVerbCatalog, playerTurnFieldDefs } from "./playerTurnPanel.js";
import {
  DEFAULT_AREA_ID,
  activeAreaView,
  asArray,
  normalizeSnapshot,
  objectOccupiesTile,
} from "./snapshot.js";

let menuEl;
let modalBackdrop;
let modalTitle;
let modalForm;
let modalError;
let toastEl;
let getSnapshot = () => null;
let onStateChanged = async () => {};
let onRunAgentTurn = async () => {};
let getCoordinateMode = () => "full";
/** Optional async handler when the shared modal is dismissed (Escape / backdrop / Cancel). */
let onModalDismiss = null;

export function initUi({ getSnapshotFn, onStateChangedFn, onRunAgentTurnFn, getCoordinateModeFn }) {
  getSnapshot = getSnapshotFn;
  onStateChanged = onStateChangedFn;
  onRunAgentTurn = onRunAgentTurnFn ?? onRunAgentTurn;
  getCoordinateMode = getCoordinateModeFn ?? getCoordinateMode;

  menuEl = document.getElementById("context-menu");
  modalBackdrop = document.getElementById("modal-backdrop");
  modalTitle = document.getElementById("modal-title");
  modalForm = document.getElementById("modal-form");
  modalError = document.getElementById("modal-error");
  toastEl = document.getElementById("toast");

  initObjectActions({
    getSnapshotFn: getSnapshot,
    onStateChangedFn: onStateChanged,
    showToastFn: showToast,
    modalTitleEl: modalTitle,
    modalFormEl: modalForm,
    modalErrorEl: modalError,
    modalBackdropEl: modalBackdrop,
    closeModal,
  });

  document.getElementById("modal-cancel").addEventListener("click", () => {
    void dismissModal();
  });
  document.getElementById("modal-backdrop").addEventListener("click", (e) => {
    if (e.target === modalBackdrop) void dismissModal();
  });
  document.addEventListener("click", () => hideMenu());
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      hideMenu();
      void dismissModal();
    }
  });
}

function tileCoordsFromContextEvent(e) {
  const tile = e.target.closest(".tile");
  if (tile) {
    return { x: Number(tile.dataset.x), y: Number(tile.dataset.y) };
  }

  const grid = activeAreaView(getSnapshot())?.grid;
  const gridNode = document.getElementById("grid");
  if (!grid || !gridNode) return null;

  const rect = gridNode.getBoundingClientRect();
  const relX = e.clientX - rect.left;
  const relY = e.clientY - rect.top;
  if (relX < 0 || relY < 0 || relX >= rect.width || relY >= rect.height) {
    return null;
  }

  const x = grid.min_x + Math.floor(relX / CELL_SIZE);
  const y = grid.min_y + Math.floor(relY / CELL_SIZE);
  if (x < grid.min_x || x > grid.max_x || y < grid.min_y || y > grid.max_y) {
    return null;
  }
  return { x, y };
}

export function bindGridContextMenu(gridEl) {
  gridEl.addEventListener("contextmenu", (e) => {
    e.preventDefault();
    if (isSceneEditMode()) {
      return;
    }
    hideMenu();

    const coords = tileCoordsFromContextEvent(e);
    if (!coords) return;

    const { x, y } = coords;
    const at = entitiesAt(x, y);
    const count = at.agents.length + at.objects.length;

    if (count > 1) {
      showManageTileMenu(e.clientX, e.clientY, x, y, at);
    } else if (count === 0) {
      showEmptyTileMenu(e.clientX, e.clientY, x, y);
    } else {
      const entity = at.agents[0] || at.objects[0];
      const kind = at.agents.length ? "agent" : "object";
      void showEntityMenu(e.clientX, e.clientY, kind, entity.id);
    }
  });
}

function entitiesAt(x, y) {
  const snap = activeAreaView(getSnapshot());
  if (!snap?.grid) return { agents: [], objects: [] };
  const agents = asArray(snap.agents).filter((a) => a.position[0] === x && a.position[1] === y);
  const objects = asArray(snap.objects).filter((o) => objectOccupiesTile(o, x, y));
  return { agents, objects };
}

function findEntity(kind, id) {
  const snap = activeAreaView(getSnapshot());
  if (!snap) return null;
  const list = kind === "agent" ? asArray(snap.agents) : asArray(snap.objects);
  return list.find((e) => e.id === id) || null;
}

function findAgentWithArea(agentId) {
  const snap = normalizeSnapshot(getSnapshot());
  const entity = asArray(snap?.agents).find((a) => a.id === agentId);
  if (!entity) return null;
  const areaId = entity.area_id ?? activeAreaView(getSnapshot())?.active_area_id ?? DEFAULT_AREA_ID;
  return { entity, areaId };
}

function findObjectWithArea(objectId) {
  const snap = normalizeSnapshot(getSnapshot());
  if (!snap?.areas) return null;
  for (const [areaId, block] of Object.entries(snap.areas)) {
    const entity = asArray(block.objects).find((o) => o.id === objectId);
    if (entity) {
      return { entity, areaId };
    }
  }
  return null;
}

function listAreaOptions() {
  const snap = normalizeSnapshot(getSnapshot());
  return Object.keys(snap?.areas ?? {})
    .sort()
    .map((areaId) => ({ value: areaId, label: areaId }));
}

function showMenu(x, y, items) {
  menuEl.innerHTML = "";
  for (const item of items) {
    if (item.hidden) {
      continue;
    }
    if (item.separator) {
      const sep = document.createElement("div");
      sep.className = "context-menu-sep";
      menuEl.appendChild(sep);
      continue;
    }
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = item.className
      ? `context-menu-item ${item.className}`
      : "context-menu-item";
    btn.textContent = item.label;
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      hideMenu();
      item.action();
    });
    menuEl.appendChild(btn);
  }
  menuEl.classList.remove("hidden");
  menuEl.style.left = `${x}px`;
  menuEl.style.top = `${y}px`;
}

function hideMenu() {
  menuEl.classList.add("hidden");
}

function showEmptyTileMenu(x, y, tileX, tileY) {
  showMenu(x, y, [
    {
      label: "Load…",
      action: () => openLoadEntityModal(tileX, tileY),
    },
    {
      label: "Create object here…",
      action: () => openCreateObjectModal(tileX, tileY),
    },
    {
      label: "Create hidden trigger…",
      action: () => openCreateHiddenTriggerModal(tileX, tileY),
    },
    {
      label: "Create agent here…",
      action: () => openCreateAgentModal(tileX, tileY),
    },
  ]);
}

function showManageTileMenu(x, y, tileX, tileY, at) {
  const items = [
    {
      label: "Load…",
      action: () => openLoadEntityModal(tileX, tileY),
    },
    {
      label: "Create object here…",
      action: () => openCreateObjectModal(tileX, tileY),
    },
    {
      label: "Create hidden trigger…",
      action: () => openCreateHiddenTriggerModal(tileX, tileY),
    },
    {
      label: "Create agent here…",
      action: () => openCreateAgentModal(tileX, tileY),
    },
    { separator: true },
  ];
  for (const agent of asArray(at.agents)) {
    items.push({
      label: `Agent: ${agent.name}`,
      action: () => {
        void showEntityMenu(x, y, "agent", agent.id);
      },
    });
  }
  for (const object of asArray(at.objects)) {
    items.push({
      label: `Object: ${object.name}`,
      action: () => showEntityMenu(x, y, "object", object.id),
    });
  }
  showMenu(x, y, items);
}

async function showEntityMenu(x, y, kind, id) {
  const entity = findEntity(kind, id);
  if (!entity) return;

  if (kind === "agent") {
    const agentCtx = findAgentWithArea(id) ?? {
      entity,
      areaId: activeAreaView(getSnapshot())?.active_area_id,
    };
    let runTurnClass = "context-menu-item--ok";
    if (!entity.is_player) {
      try {
        const budget = await getPrompt(entity.id);
        if (budget.over_limit) {
          runTurnClass = "context-menu-item--danger";
        } else if (budget.over_warning) {
          runTurnClass = "context-menu-item--warn";
        }
      } catch {
        runTurnClass = "";
      }
    }
    showMenu(x, y, [
      {
        label: "Run turn ▶",
        action: () => onRunAgentTurn(entity.id),
        hidden: Boolean(entity.is_player),
        className: runTurnClass,
      },
      {
        label: "Manual turn…",
        action: () => {
          openPlayerTurnModal(
            entity.name,
            (compoundTurn) => onRunAgentTurn(entity.id, compoundTurn),
            getCoordinateMode(),
          );
        },
        hidden: !entity.is_player,
      },
      {
        label: "Copy player join link",
        action: () => {
          void copyPlayerJoinLink(entity.id);
        },
        hidden: !entity.is_player,
      },
      {
        label: "Play as this agent",
        action: () => runActiveAgent(entity.id),
      },
      {
        label: "Edit…",
        action: () => openEditAgentModal(agentCtx.entity, agentCtx.areaId),
      },
      {
        label: "Save as…",
        action: () => openSaveEntityModal("agent", entity),
      },
      {
        label: "Delete",
        action: () => runDelete(`delete-agent ${entity.id}`, entity.name),
      },
    ]);
  } else {
    const objectCtx = findObjectWithArea(id) ?? {
      entity,
      areaId: activeAreaView(getSnapshot())?.active_area_id,
    };
    showMenu(x, y, [
      {
        label: "Edit…",
        action: () => openEditObjectModal(objectCtx.entity, objectCtx.areaId),
      },
      { label: "Manage actions…", action: () => openManageObjectActionsModal(entity) },
      {
        label: "Save as…",
        action: () => openSaveEntityModal("object", entity),
      },
      entity.hidden
        ? {
            label: "Reveal",
            action: () => runCommand(`edit-object ${entity.id} hidden false`),
          }
        : {
            label: "Hide",
            action: () => runCommand(`edit-object ${entity.id} hidden true`),
          },
      {
        label: "Delete",
        action: () => runDelete(`delete-object ${entity.id}`, entity.name),
      },
    ]);
  }
}

async function copyPlayerJoinLink(agentId) {
  try {
    const data = await createPlayerSeat(agentId);
    const url = data.join_url;
    if (!url) throw new Error("No join URL returned.");
    await navigator.clipboard.writeText(url);
    const who = data.agent_name || agentId;
    showToast(`Copied join link for ${who}: ${url}`, false);
  } catch (err) {
    showToast(String(err.message || err), true);
  }
}

async function runCommand(line) {
  const result = await postCommand(line);
  if (!result.ok) {
    showToast(result.message, true);
    return result;
  }
  showToast(result.message, false);
  await onStateChanged(result.snapshot);
  return result;
}

async function runActiveAgent(nameOrId) {
  const result = await postActiveAgent(nameOrId);
  if (!result.ok) {
    showToast(result.message, true);
    return;
  }
  showToast(result.message, false);
  await onStateChanged();
}

async function runDelete(line, name) {
  if (!window.confirm(`Delete ${name}?`)) return;
  await runCommand(line);
}

function showToast(message, isError) {
  toastEl.textContent = message;
  toastEl.classList.toggle("toast-error", isError);
  toastEl.classList.remove("hidden");
  clearTimeout(showToast._timer);
  showToast._timer = setTimeout(() => toastEl.classList.add("hidden"), 4000);
}

function closeModal() {
  onModalDismiss = null;
  modalBackdrop.classList.add("hidden");
  modalBackdrop.querySelector(".modal")?.classList.remove("modal--wide");
  modalForm.innerHTML = "";
  modalError.textContent = "";
  const cancelBtn = document.getElementById("modal-cancel");
  if (cancelBtn) {
    cancelBtn.classList.remove("hidden");
    cancelBtn.textContent = "Cancel";
  }
}

async function dismissModal() {
  if (modalBackdrop.classList.contains("hidden")) return;
  const handler = onModalDismiss;
  onModalDismiss = null;
  try {
    if (handler) await handler();
  } finally {
    closeModal();
  }
}

function syncConditionalModalFields(form) {
  const conditional = form.querySelectorAll(".modal-field-conditional");
  for (const wrap of conditional) {
    const triggerName = wrap.dataset.showWhenField;
    const allowed = (wrap.dataset.showWhenValues || "")
      .split(",")
      .map((v) => v.trim())
      .filter(Boolean);
    const trigger = form.elements[triggerName];
    const current = trigger?.type === "checkbox" ? trigger.checked : trigger?.value;
    wrap.hidden = !allowed.includes(String(current));
  }
}

const MODAL_GROUPS = {
  basic: { title: "Basic", open: true },
  descriptions: { title: "Descriptions", open: false },
  placement: { title: "Placement", open: false },
  simulation: { title: "Simulation", open: false },
  memory: { title: "Memory options", open: false },
  plugins: { title: "Plugins", open: false },
  advanced: { title: "Advanced", open: false },
};

function resolveFieldGroup(field) {
  if (field.group) return field.group;
  if (field.location) return "placement";
  if (field.advanced) return "advanced";
  return "basic";
}

function ensureModalGroup(form, groupId) {
  const config = MODAL_GROUPS[groupId] ?? { title: groupId, open: false };
  let details = form.querySelector(`.modal-group[data-group="${groupId}"]`);
  if (!details) {
    details = document.createElement("details");
    details.className = "modal-group";
    details.dataset.group = groupId;
    if (config.open) details.open = true;
    const summary = document.createElement("summary");
    summary.textContent = config.title;
    details.appendChild(summary);
    const body = document.createElement("div");
    body.className = "modal-group-body";
    details.appendChild(body);
    form.appendChild(details);
  }
  return details.querySelector(".modal-group-body");
}

function ensureAdvancedSection(form) {
  return ensureModalGroup(form, "advanced");
}

function ensureLocationSection(form) {
  return ensureModalGroup(form, "placement");
}

function appendModalField(form, field) {
  if (field.type === "context") {
    const context = document.createElement("p");
    context.className = "modal-context";
    context.textContent = field.text ?? "";
    ensureModalGroup(form, resolveFieldGroup(field)).appendChild(context);
    return;
  }

  const wrap = document.createElement("label");
  wrap.className = "modal-field";
  if (field.showWhen) {
    wrap.classList.add("modal-field-conditional");
    wrap.dataset.showWhenField = field.showWhen.field;
    wrap.dataset.showWhenValues = field.showWhen.values.join(",");
  }
  const label = document.createElement("span");
  label.textContent = field.label;
  wrap.appendChild(label);

  let input;
  if (field.type === "checkbox") {
    input = document.createElement("input");
    input.type = "checkbox";
    input.checked = !!field.value;
  } else if (field.type === "textarea") {
    input = document.createElement("textarea");
    input.rows = field.rows || 2;
    input.value = field.value ?? "";
  } else if (field.type === "multiselect") {
    input = document.createElement("select");
    input.multiple = true;
    const optionCount = field.options?.length || 0;
    input.size = Math.min(Math.max(optionCount, 3), 8);
    for (const opt of field.options || []) {
      const option = document.createElement("option");
      option.value = opt.value;
      option.textContent = opt.label;
      if (field.value?.includes(opt.value)) {
        option.selected = true;
      }
      input.appendChild(option);
    }
  } else if (field.type === "select") {
    input = document.createElement("select");
    for (const opt of field.options || []) {
      const option = document.createElement("option");
      option.value = opt.value;
      option.textContent = opt.label;
      if (String(opt.value) === String(field.value ?? "")) {
        option.selected = true;
      }
      input.appendChild(option);
    }
  } else if (field.type === "readonly") {
    input = document.createElement("input");
    input.type = "text";
    input.value = field.value ?? "";
    input.readOnly = true;
    input.className = "modal-readonly";
  } else {
    input = document.createElement("input");
    input.type = field.type || "text";
    input.value = field.value ?? "";
  }
  input.name = field.name;
  if (field.required) input.required = true;
  if (field.placeholder) input.placeholder = field.placeholder;
  wrap.appendChild(input);

  const groupId = resolveFieldGroup(field);
  const parent = ensureModalGroup(form, groupId);
  parent.appendChild(wrap);
}

function collectModalFormData(formEl, fields) {
  const data = {};
  for (const field of fields) {
    if (field.type === "context" || field.type === "readonly" || !field.name) continue;
    const el = formEl.elements[field.name];
    if (!el) continue;
    data[field.name] =
      field.type === "checkbox"
        ? el.checked
        : field.type === "multiselect"
          ? Array.from(el.selectedOptions).map((option) => option.value)
          : el.value.trim();
  }
  return data;
}

function openModal(title, fields, onSubmit, { submitLabel = "Save", actions = null } = {}) {
  modalTitle.textContent = title;
  modalForm.innerHTML = "";
  modalError.textContent = "";

  for (const field of fields) {
    appendModalField(modalForm, field);
  }

  syncConditionalModalFields(modalForm);
  for (const el of modalForm.querySelectorAll("select, input[type=checkbox]")) {
    el.addEventListener("change", () => syncConditionalModalFields(modalForm));
  }

  const runSubmit = async (handler) => {
    modalError.textContent = "";
    try {
      const shouldClose = await handler(collectModalFormData(modalForm, fields));
      if (shouldClose === false) return;
      closeModal();
    } catch (err) {
      modalError.textContent = String(err.message || err);
    }
  };

  const actionsEl = document.createElement("div");
  actionsEl.className = "modal-actions";

  if (actions?.length) {
    for (const action of actions) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = action.label;
      if (action.className) btn.className = action.className;
      btn.addEventListener("click", () => runSubmit(action.onSubmit));
      actionsEl.appendChild(btn);
    }
    modalForm.onsubmit = (e) => {
      e.preventDefault();
      void runSubmit(actions[0].onSubmit);
    };
  } else {
    const submit = document.createElement("button");
    submit.type = "submit";
    submit.textContent = submitLabel;
    actionsEl.appendChild(submit);
    modalForm.onsubmit = async (e) => {
      e.preventDefault();
      await runSubmit(onSubmit);
    };
  }

  modalForm.appendChild(actionsEl);
  modalBackdrop.classList.remove("hidden");
}

/**
 * Confirm-style modal with context paragraphs and custom OK/Cancel actions.
 * Backdrop / Escape / shared Cancel run *onDismiss* (defaults to *onCancel*).
 */
export function openConfirmModal({
  title,
  paragraphs = [],
  okLabel = "OK",
  cancelLabel = "Cancel",
  onOk,
  onCancel,
  onDismiss = null,
  hideSharedCancel = true,
} = {}) {
  const cancelBtn = document.getElementById("modal-cancel");
  if (hideSharedCancel && cancelBtn) {
    cancelBtn.classList.add("hidden");
  }

  onModalDismiss = onDismiss || onCancel || null;

  const fields = paragraphs.map((text) => ({ type: "context", text }));

  openModal(title, fields, null, {
    actions: [
      {
        label: okLabel,
        onSubmit: async () => {
          onModalDismiss = null;
          if (onOk) await onOk();
        },
      },
      {
        label: cancelLabel,
        className: "modal-cancel-action",
        onSubmit: async () => {
          onModalDismiss = null;
          if (onCancel) await onCancel();
        },
      },
    ],
  });
}

function objectHiddenField(hidden = false) {
  return {
    name: "hidden",
    label: "Hidden from agent vision",
    type: "checkbox",
    value: !!hidden,
    group: "simulation",
  };
}

function privateDataField(value = "") {
  return {
    name: "privateData",
    label: "Private data (custom apps only)",
    value: value ?? "",
    type: "textarea",
    rows: 3,
    placeholder: "{}",
    group: "advanced",
  };
}

/**
 * Load enabled plugin form sections and flatten to modal fields.
 * @returns {Promise<{fields: object[], sections: object[]}>}
 */
async function loadPluginEntityFormFields(kind, entityId = null) {
  try {
    const data = await fetchEntityFormSections(kind, entityId);
    const sections = data.sections || [];
    const fields = [];
    for (const section of sections) {
      fields.push({
        type: "context",
        text: section.title || section.plugin_label || section.plugin_id,
        group: "plugins",
      });
      for (const field of section.fields || []) {
        fields.push(field);
      }
    }
    return { fields, sections };
  } catch {
    return { fields: [], sections: [] };
  }
}

async function resolvePrivateDataWithPlugins(kind, privateDataText, formData) {
  const values = {};
  for (const [key, value] of Object.entries(formData || {})) {
    if (String(key).startsWith("efs_")) {
      values[key] = value;
    }
  }
  if (!Object.keys(values).length) {
    return String(privateDataText ?? "");
  }
  const merged = await postMergeEntityFormPrivateData({
    kind,
    private_data: privateDataText ?? "",
    values,
  });
  return merged.private_data ?? "";
}

async function persistPrivateDataIfChanged(entityId, value, previous) {
  const next = String(value ?? "");
  const prev = String(previous ?? "");
  if (next === prev) return null;
  const result = await postEntityPrivateData(entityId, next);
  if (!result.ok) throw new Error(result.message);
  return result;
}

/**
 * Run an edit command, then private_data. "No changes applied" on the command is
 * OK when private_data actually changed (edit_agent/edit_object ignore that field).
 */
async function commitEditAndPrivateData(editResult, entityId, nextPrivate, prevPrivate) {
  const noOpEdit = !editResult.ok && /no changes applied/i.test(String(editResult.message || ""));
  if (!editResult.ok && !noOpEdit) {
    throw new Error(editResult.message);
  }
  const privateResult = await persistPrivateDataIfChanged(entityId, nextPrivate, prevPrivate);
  if (noOpEdit && !privateResult) {
    throw new Error(editResult.message);
  }
  return {
    message: privateResult?.message ?? editResult.message,
    snapshot: privateResult?.snapshot ?? editResult.snapshot,
  };
}

function objectMovementFields({ blocksMovement, movementExceptions }) {
  const blocking = blocksMovement !== false;
  return [
    {
      name: "blocksMovement",
      label: "Blocks movement",
      type: "checkbox",
      value: blocking,
      group: "simulation",
    },
    {
      name: "movementExceptions",
      label: "Movement exceptions (entity ids, comma-separated)",
      value: movementExceptions ?? "",
      placeholder: "agent_01, obj_door_01",
      showWhen: { field: "blocksMovement", values: ["true"] },
      group: "simulation",
    },
  ];
}

function openCreateObjectModal(x, y) {
  void (async () => {
    const pluginForm = await loadPluginEntityFormFields("object");
    openModal(
      "Create object",
      [
        { name: "name", label: "Name", value: "New Object", required: true, group: "basic" },
        {
          name: "pdesc",
          label: "Passive description",
          value: "An object.",
          type: "textarea",
          group: "descriptions",
        },
        {
          name: "desc",
          label: "Detailed description",
          value: "A new object.",
          type: "textarea",
          group: "descriptions",
        },
        {
          name: "x",
          label: "X",
          value: String(x),
          type: "number",
          required: true,
          group: "placement",
        },
        {
          name: "y",
          label: "Y",
          value: String(y),
          type: "number",
          required: true,
          group: "placement",
        },
        {
          name: "width",
          label: "Width (tiles)",
          value: "1",
          type: "number",
          required: true,
          group: "placement",
        },
        {
          name: "height",
          label: "Height (tiles)",
          value: "1",
          type: "number",
          required: true,
          group: "placement",
        },
        ...objectMovementFields({ blocksMovement: true, movementExceptions: "" }),
        objectHiddenField(false),
        {
          name: "appearance",
          label: "Token image path",
          value: "",
          placeholder: "tokens/my-object.svg",
          group: "advanced",
        },
        ...pluginForm.fields,
        privateDataField(),
      ],
      async (data) => {
        const line = buildCreateObject({
          name: data.name,
          pdesc: data.pdesc,
          desc: data.desc,
          appearance: data.appearance,
          x: data.x,
          y: data.y,
          width: data.width,
          height: data.height,
          blocksMovement: data.blocksMovement,
          movementExceptions: data.movementExceptions,
          hidden: data.hidden,
        });
        const result = await postCommand(line);
        if (!result.ok) throw new Error(result.message);
        const objectId = parseCreatedObjectId(result.message);
        if (!objectId) throw new Error("Created object id not found in response.");
        const privateData = await resolvePrivateDataWithPlugins(
          "object",
          data.privateData,
          data,
        );
        const privateResult = await persistPrivateDataIfChanged(objectId, privateData, "");
        showToast(privateResult?.message ?? result.message, false);
        await onStateChanged(privateResult?.snapshot ?? result.snapshot);
      },
    );
  })();
}

function openCreateHiddenTriggerModal(x, y) {
  openModal(
    "Create hidden trigger",
    [
      { name: "name", label: "Object name", value: "Trap", required: true },
      {
        name: "actionName",
        label: "Trigger action name",
        value: "trip",
        required: true,
      },
      {
        name: "areaEvent",
        label: "Area event text (passive)",
        value: "{actor} steps on the trap.",
        type: "textarea",
        required: true,
      },
      { name: "x", label: "X", value: String(x), type: "number", required: true },
      { name: "y", label: "Y", value: String(y), type: "number", required: true },
      {
        name: "width",
        label: "Width (tiles)",
        value: "1",
        type: "number",
        required: true,
      },
      {
        name: "height",
        label: "Height (tiles)",
        value: "1",
        type: "number",
        required: true,
      },
      {
        name: "range",
        label: "Range (Chebyshev tiles beyond footprint)",
        value: "0",
        type: "number",
        required: true,
      },
      {
        name: "haltMovement",
        label: "Halt movement on trigger",
        type: "checkbox",
        value: true,
      },
      {
        name: "deleteAfterTrigger",
        label: "Delete object after trigger",
        type: "checkbox",
        value: true,
      },
      {
        name: "triggerExceptions",
        label: "Trigger exceptions (agent ids, comma-separated)",
        value: "",
        placeholder: "agent_01",
        advanced: true,
      },
    ],
    async (data) => {
      const { createLine, actionLine } = buildCreateHiddenTrigger({
        name: data.name,
        x: data.x,
        y: data.y,
        width: data.width,
        height: data.height,
        areaEvent: data.areaEvent,
        actionName: data.actionName,
        range: data.range,
        haltMovement: data.haltMovement,
        deleteAfterTrigger: data.deleteAfterTrigger,
        triggerExceptions: data.triggerExceptions,
      });
      const createResult = await postCommand(createLine);
      if (!createResult.ok) throw new Error(createResult.message);

      let objectId = parseCreatedObjectId(createResult.message);
      if (!objectId) {
        const snap = normalizeSnapshot(createResult.snapshot ?? (await getState()));
        const objects = Object.values(snap?.areas || {}).flatMap((block) => block.objects || []);
        const created = objects.find(
          (obj) =>
            obj.name === data.name &&
            obj.position?.[0] === Number(data.x) &&
            obj.position?.[1] === Number(data.y),
        );
        objectId = created?.id ?? null;
      }
      if (!objectId) {
        throw new Error("Created object not found in snapshot.");
      }
      const addLine = actionLine.replace("__OBJECT_ID__", objectId);
      const addResult = await postCommand(addLine);
      if (!addResult.ok) throw new Error(addResult.message);
      showToast(addResult.message, false);
      await onStateChanged(addResult.snapshot ?? createResult.snapshot);
    },
    { submitLabel: "Create" },
  );
}

function openCreateAgentModal(x, y) {
  void (async () => {
    let catalog;
    try {
      catalog = await getMemoryModules();
    } catch (err) {
      showToast(String(err.message || err), true);
      return;
    }

    const fields = [
      { name: "name", label: "Name", value: "New Agent", required: true, group: "basic" },
      {
        name: "personality",
        label: "Personality (LLM)",
        value: "You are a calm agent in a small room.",
        type: "textarea",
        rows: 2,
        group: "basic",
      },
      {
        name: "memoryModule",
        label: "Memory module",
        type: "select",
        value: catalog.default_id,
        options: catalog.modules.map((mod) => ({
          value: mod.id,
          label: mod.label || mod.id,
        })),
        group: "basic",
      },
      { type: "context", text: `Creating at (${x}, ${y})`, group: "basic" },
      {
        name: "pdesc",
        label: "Passive description",
        value: "A figure.",
        type: "textarea",
        group: "descriptions",
      },
      {
        name: "desc",
        label: "Detailed description",
        value: "A new agent.",
        type: "textarea",
        group: "descriptions",
      },
      {
        name: "moveSpeed",
        label: "Move speed (steps per turn)",
        value: "",
        type: "number",
        placeholder: "blank = unlimited (teleport)",
        group: "simulation",
      },
      {
        name: "isPlayer",
        label: "Player (manual turns, no LLM)",
        type: "checkbox",
        value: false,
        group: "simulation",
      },
      ...objectMovementFields({ blocksMovement: true, movementExceptions: "" }),
      {
        name: "appearance",
        label: "Token image path",
        value: "",
        placeholder: "tokens/my-agent.svg",
        group: "advanced",
      },
      privateDataField(),
    ];

    const memoryOptionFields = [];
    for (const mod of catalog.modules) {
      for (const opt of mod.options || []) {
        const placeholder = opt.max != null ? `${opt.min}–${opt.max}` : `${opt.min}+`;
        memoryOptionFields.push({
          name: memoryOptionFieldName(opt.flag),
          label: opt.label,
          type: "number",
          value: String(opt.default),
          placeholder,
          showWhen: { field: "memoryModule", values: [mod.id] },
          group: "memory",
        });
      }
    }
    const memoryIndex = fields.findIndex((field) => field.name === "memoryModule") + 1;
    fields.splice(memoryIndex, 0, ...memoryOptionFields);

    openModal("Create agent", fields, async (data) => {
      const selectedModule = catalog.modules.find((mod) => mod.id === data.memoryModule);
      const memoryOptions = {};
      for (const opt of selectedModule?.options || []) {
        const key = memoryOptionFieldName(opt.flag);
        if (data[key]) memoryOptions[key] = data[key];
      }
      const line = buildCreateAgent({
        name: data.name,
        pdesc: data.pdesc,
        desc: data.desc,
        personality: data.personality,
        appearance: data.appearance,
        moveSpeed: data.moveSpeed,
        memoryModule: data.memoryModule,
        memoryOptions,
        isPlayer: data.isPlayer,
        blocksMovement: data.blocksMovement,
        movementExceptions: data.blocksMovement ? data.movementExceptions : "",
        x,
        y,
      });
      const result = await postCommand(line);
      if (!result.ok) throw new Error(result.message);
      const agentId = parseCreatedAgentId(result.message);
      if (!agentId) throw new Error("Created agent id not found in response.");
      const privateResult = await persistPrivateDataIfChanged(agentId, data.privateData, "");
      showToast(privateResult?.message ?? result.message, false);
      await onStateChanged(privateResult?.snapshot ?? result.snapshot);
    });
  })();
}

function openEditObjectModal(entity, areaId) {
  const resolvedAreaId = areaId ?? activeAreaView(getSnapshot())?.active_area_id ?? DEFAULT_AREA_ID;
  const areaOptions = listAreaOptions();

  void (async () => {
    const pluginForm = await loadPluginEntityFormFields("object", entity.id);
    openModal(
      `Edit object — ${entity.name}`,
      [
        { name: "name", label: "Name", value: entity.name, required: true, group: "basic" },
        {
          name: "pdesc",
          label: "Passive description",
          value: entity.passive_description ?? "",
          type: "textarea",
          group: "descriptions",
        },
        {
          name: "desc",
          label: "Detailed description",
          value: entity.description ?? "",
          type: "textarea",
          group: "descriptions",
        },
        {
          name: "areaId",
          label: "Area",
          type: "select",
          value: resolvedAreaId,
          options: areaOptions,
          group: "placement",
        },
        {
          name: "x",
          label: "X",
          value: String(entity.position[0]),
          type: "number",
          required: true,
          group: "placement",
        },
        {
          name: "y",
          label: "Y",
          value: String(entity.position[1]),
          type: "number",
          required: true,
          group: "placement",
        },
        {
          name: "width",
          label: "Width (tiles)",
          value: String(entity.width ?? 1),
          type: "number",
          required: true,
          group: "placement",
        },
        {
          name: "height",
          label: "Height (tiles)",
          value: String(entity.height ?? 1),
          type: "number",
          required: true,
          group: "placement",
        },
        ...objectMovementFields({
          blocksMovement: entity.blocks_movement !== false,
          movementExceptions: (entity.movement_exceptions || []).join(", "),
        }),
        objectHiddenField(!!entity.hidden),
        {
          name: "appearance",
          label: "Token image path",
          value: entity.appearance ?? "",
          placeholder: "tokens/my-object.svg",
          group: "advanced",
        },
        ...pluginForm.fields,
        privateDataField(entity.private_data),
      ],
      async (data) => {
        const line = buildEditObject({
          id: entity.id,
          name: data.name,
          pdesc: data.pdesc || undefined,
          desc: data.desc || undefined,
          appearance: data.appearance,
          areaId: data.areaId,
          sourceAreaId: resolvedAreaId,
          x: data.x,
          y: data.y,
          width: data.width,
          height: data.height,
          blocksMovement: data.blocksMovement,
          movementExceptions: data.blocksMovement ? data.movementExceptions : "",
          hidden: data.hidden,
        });
        const result = await postCommand(line);
        const privateData = await resolvePrivateDataWithPlugins(
          "object",
          data.privateData,
          data,
        );
        const committed = await commitEditAndPrivateData(
          result,
          entity.id,
          privateData,
          entity.private_data,
        );
        showToast(committed.message, false);
        await onStateChanged(committed.snapshot);
      },
    );
  })();
}

function openEditAgentModal(entity, areaId) {
  const resolvedAreaId = areaId ?? activeAreaView(getSnapshot())?.active_area_id ?? DEFAULT_AREA_ID;
  const areaOptions = listAreaOptions();

  openModal(
    `Edit agent — ${entity.name}`,
    [
      { name: "name", label: "Name", value: entity.name, required: true, group: "basic" },
      {
        name: "personality",
        label: "Personality (LLM)",
        value: entity.personality ?? "",
        type: "textarea",
        group: "basic",
      },
      {
        name: "pdesc",
        label: "Passive description",
        value: entity.passive_description ?? "",
        type: "textarea",
        group: "descriptions",
      },
      {
        name: "desc",
        label: "Detailed description",
        value: entity.description ?? "",
        type: "textarea",
        group: "descriptions",
      },
      {
        name: "moveSpeed",
        label: "Move speed (steps per turn)",
        value: entity.move_speed != null ? String(entity.move_speed) : "",
        type: "number",
        placeholder: "blank = unlimited (teleport)",
        group: "simulation",
      },
      {
        name: "isPlayer",
        label: "Player (manual turns, no LLM)",
        type: "checkbox",
        value: Boolean(entity.is_player),
        group: "simulation",
      },
      ...objectMovementFields({
        blocksMovement: entity.blocks_movement === true,
        movementExceptions: (entity.movement_exceptions || []).join(", "),
      }),
      {
        name: "memoryModule",
        label: "Memory module (set at creation)",
        type: "readonly",
        value: entity.memory_module ?? "recent_turns",
        group: "simulation",
      },
      {
        name: "areaId",
        label: "Area",
        type: "select",
        value: resolvedAreaId,
        options: areaOptions,
        group: "placement",
      },
      {
        name: "x",
        label: "X",
        value: String(entity.position[0]),
        type: "number",
        required: true,
        group: "placement",
      },
      {
        name: "y",
        label: "Y",
        value: String(entity.position[1]),
        type: "number",
        required: true,
        group: "placement",
      },
      {
        name: "appearance",
        label: "Token image path",
        value: entity.appearance ?? "",
        placeholder: "tokens/my-agent.svg",
        group: "advanced",
      },
      privateDataField(entity.private_data),
    ],
    async (data) => {
      const line = buildEditAgent({
        id: entity.id,
        name: data.name,
        pdesc: data.pdesc || undefined,
        desc: data.desc || undefined,
        personality: data.personality || undefined,
        appearance: data.appearance,
        moveSpeed: data.moveSpeed,
        isPlayer: data.isPlayer,
        blocksMovement: data.blocksMovement,
        movementExceptions: data.blocksMovement ? data.movementExceptions : "",
        areaId: data.areaId,
        sourceAreaId: resolvedAreaId,
        x: data.x,
        y: data.y,
      });
      const result = await postCommand(line);
      const committed = await commitEditAndPrivateData(
        result,
        entity.id,
        data.privateData,
        entity.private_data,
      );
      showToast(committed.message, false);
      await onStateChanged(committed.snapshot);
    },
  );
}

function buildAgentMultiselectOptions(snapshot) {
  const snap = normalizeSnapshot(snapshot);
  return asArray(snap?.agents).map((agent) => {
    const areaTag = agent.area_id ? ` [${agent.area_id}]` : "";
    const playerTag = agent.is_player ? " (player)" : "";
    return {
      value: agent.id,
      label: `${agent.name} (${agent.id})${playerTag}${areaTag}`,
    };
  });
}

function openEmitEventModal() {
  const agentOptions = buildAgentMultiselectOptions(getSnapshot());
  openModal(
    "Emit area event",
    [
      {
        name: "text",
        label: "Event text",
        value: "Thunder rumbles overhead.",
        type: "textarea",
        rows: 3,
        required: true,
      },
      {
        name: "agent_ids",
        label: "Recipients (optional — leave empty for all agents in active area)",
        type: "multiselect",
        value: [],
        options: agentOptions,
      },
    ],
    async (data) => {
      const result = await postEvent(data.text, data.agent_ids);
      if (!result.ok) throw new Error(result.message);
      showToast(result.message, false);
      await onStateChanged(result.snapshot);
    },
    { submitLabel: "Emit" },
  );
}

export function bindEmitEventButton(buttonEl) {
  buttonEl.addEventListener("click", () => openEmitEventModal());
}

export async function openPlayerTurnModal(agentName, onSubmit, coordinateMode = "full") {
  await loadPlayerTurnVerbCatalog();
  openModal(
    `Player turn — ${agentName}`,
    playerTurnFieldDefs(coordinateMode),
    async (data) => {
      if (data.action === "interact" && (!data.target?.trim() || !data.verb?.trim())) {
        throw new Error("Interact turns require target and verb.");
      }
      if (data.action === "emote" && !data.verb?.trim()) {
        throw new Error("Emote turns require a verb (target is optional).");
      }
      if (data.action === "verb" && !String(data.turn_verb ?? data.verb ?? "").trim()) {
        throw new Error("Verb turns require a registered turn verb.");
      }
      await onSubmit(buildCompoundTurnPayload(data));
    },
    { submitLabel: "Run turn" },
  );
}

export function bindActiveAgentSelect(selectEl, onChange) {
  selectEl.addEventListener("change", async () => {
    const value = selectEl.value;
    if (!value) return;
    try {
      const result = await postActiveAgent(value);
      if (!result.ok) {
        showToast(result.message, true);
        return;
      }
      showToast(result.message, false);
      await onChange();
    } catch (err) {
      showToast(String(err.message || err), true);
    }
  });
}

export function bindActiveAreaSelect(selectEl, onChange) {
  if (!selectEl) return;
  selectEl.addEventListener("change", async () => {
    const value = selectEl.value;
    if (!value) return;
    try {
      const result = await postActiveArea(value);
      if (!result.ok) {
        showToast(result.message, true);
        return;
      }
      showToast(result.message, false);
      await onChange(result.snapshot);
    } catch (err) {
      showToast(String(err.message || err), true);
    }
  });
}

export function renderActiveAreaSelect(selectEl, snapshot) {
  if (!selectEl || !snapshot) return;
  const normalized = normalizeSnapshot(snapshot);
  const areaIds = normalized?.areas ? Object.keys(normalized.areas).sort() : [];
  const current = selectEl.value;
  selectEl.innerHTML = "";
  for (const areaId of areaIds) {
    const opt = document.createElement("option");
    opt.value = areaId;
    opt.textContent = areaId;
    if (areaId === normalized.active_area_id) opt.selected = true;
    selectEl.appendChild(opt);
  }
  if (current && [...selectEl.options].some((o) => o.value === current)) {
    selectEl.value = current;
  }
}

export function renderActiveAgentSelect(selectEl, snapshot) {
  if (!selectEl || !snapshot) return;
  const snap = normalizeSnapshot(snapshot);
  const agents = asArray(snap.agents);
  const current = selectEl.value;
  selectEl.innerHTML = "";
  for (const agent of agents) {
    const opt = document.createElement("option");
    opt.value = agent.id;
    const areaTag = agent.area_id ? ` [${agent.area_id}]` : "";
    const playerTag = agent.is_player ? " (player)" : "";
    opt.textContent = `${agent.name} (${agent.id})${playerTag}${areaTag}`;
    if (agent.id === snap.active_agent_id) opt.selected = true;
    selectEl.appendChild(opt);
  }
  if (current && [...selectEl.options].some((o) => o.value === current)) {
    selectEl.value = current;
  }
}

export function openCreateAreaModal() {
  openModal(
    "Create area",
    [
      {
        name: "id",
        label: "Area id (lowercase, e.g. attic)",
        value: "attic",
        required: true,
      },
      {
        name: "desc",
        label: "Area description",
        value: "A new area.",
        type: "textarea",
      },
      { name: "width", label: "Grid width", value: "5", type: "number", required: true },
      { name: "height", label: "Grid height", value: "5", type: "number", required: true },
    ],
    async (data) => {
      const result = await postCreateArea({
        areaId: data.id.trim().toLowerCase(),
        description: data.desc,
        width: data.width,
        height: data.height,
      });
      if (!result.ok) throw new Error(result.message);
      showToast(result.message, false);
      await onStateChanged(result.snapshot);
    },
    { submitLabel: "Create" },
  );
}

export function openEditAreaModal() {
  const snap = normalizeSnapshot(getSnapshot());
  const areaId = snap?.active_area_id;
  if (!areaId || !snap?.areas?.[areaId]) {
    showToast("No active area to edit.", true);
    return;
  }
  const block = snap.areas[areaId];
  const grid = block.grid || {};
  const width = grid.max_x != null && grid.min_x != null ? grid.max_x - grid.min_x + 1 : 5;
  const height = grid.max_y != null && grid.min_y != null ? grid.max_y - grid.min_y + 1 : 5;

  openModal(
    `Edit area — ${areaId}`,
    [
      {
        name: "desc",
        label: "Area description",
        value: block.area_description ?? "",
        type: "textarea",
      },
      { name: "width", label: "Grid width", value: String(width), type: "number", required: true },
      {
        name: "height",
        label: "Grid height",
        value: String(height),
        type: "number",
        required: true,
      },
    ],
    async (data) => {
      const result = await postEditArea({
        areaId,
        description: data.desc,
        width: data.width,
        height: data.height,
      });
      if (!result.ok) throw new Error(result.message);
      showToast(result.message, false);
      await onStateChanged(result.snapshot);
    },
  );
}

export async function openDeleteAreaModal() {
  const snap = normalizeSnapshot(getSnapshot());
  const areaId = snap?.active_area_id;
  if (!areaId) {
    showToast("No active area selected.", true);
    return;
  }
  if (!window.confirm(`Delete area "${areaId}"? It must be empty (no agents or objects).`)) {
    return;
  }
  try {
    const result = await postDeleteArea(areaId);
    if (!result.ok) {
      showToast(result.message, true);
      return;
    }
    showToast(result.message, false);
    await onStateChanged(result.snapshot);
  } catch (err) {
    showToast(String(err.message || err), true);
  }
}

export function bindAreaManageButtons({ createBtn, editBtn, deleteBtn, saveAreaBtn, loadAreaBtn }) {
  if (createBtn) createBtn.addEventListener("click", () => openCreateAreaModal());
  if (editBtn) editBtn.addEventListener("click", () => openEditAreaModal());
  if (deleteBtn) deleteBtn.addEventListener("click", () => openDeleteAreaModal());
  if (saveAreaBtn) saveAreaBtn.addEventListener("click", () => openSaveAreaTemplateModal());
  if (loadAreaBtn) loadAreaBtn.addEventListener("click", () => openLoadAreaTemplateModal());
}

function slugifyTemplateFilename(name) {
  return (
    String(name || "template")
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || "template"
  );
}

async function openSaveEntityModal(kind, entity) {
  const defaultName = `${slugifyTemplateFilename(entity.name)}.json`;
  const fields = [
    {
      name: "filename",
      label: "Filename",
      value: defaultName,
      required: true,
      group: "basic",
    },
  ];
  if (kind === "agent") {
    fields.push({
      name: "includeMemory",
      label: "Include memory (for recurring NPCs between sessions)",
      type: "checkbox",
      value: false,
      group: "basic",
    });
  }
  fields.push({
    type: "context",
    text: "Templates omit entity id and position. Save to the Studio library for quick reuse, or download a JSON file to your computer.",
    group: "basic",
  });

  openModal(`Save ${kind}`, fields, null, {
    actions: [
      {
        label: "Save as template",
        onSubmit: async (data) => {
          const result = await postSaveEntityTemplate({
            kind,
            entityId: entity.id,
            filename: data.filename,
            includeMemory: Boolean(data.includeMemory),
          });
          showToast(result.message || "Template saved.", false);
        },
      },
      {
        label: "Save as file",
        onSubmit: async (data) => {
          const { filename } = await downloadEntityTemplateFromEntity({
            kind,
            entityId: entity.id,
            filename: data.filename,
            includeMemory: Boolean(data.includeMemory),
          });
          showToast(`Saved ${filename}`, false);
        },
      },
    ],
  });
}

function pickJsonFile() {
  return new Promise((resolve, reject) => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".json,application/json";
    input.addEventListener("change", async () => {
      const file = input.files?.[0];
      if (!file) {
        resolve(null);
        return;
      }
      try {
        const text = await file.text();
        resolve({ file, template: JSON.parse(text) });
      } catch (err) {
        reject(err);
      }
    });
    input.click();
  });
}

async function openLoadEntityModal(tileX, tileY) {
  let templates = [];
  try {
    const data = await fetchEntityTemplates();
    templates = data.templates || [];
  } catch (err) {
    showToast(String(err.message || err), true);
    return;
  }

  const areaId = activeAreaView(getSnapshot())?.active_area_id ?? DEFAULT_AREA_ID;
  const templateOptions = templates.length
    ? templates.map((item) => ({
        value: item.id,
        label: `${item.name} (${item.kind})`,
      }))
    : [{ value: "", label: "No templates saved", disabled: true }];

  openModal(
    "Load entity",
    [
      {
        name: "templateId",
        label: "Studio template",
        type: "select",
        value: templates[0]?.id ?? "",
        required: false,
        options: templateOptions,
        group: "basic",
      },
      {
        name: "x",
        label: "X",
        value: String(tileX),
        type: "number",
        required: true,
        group: "placement",
      },
      {
        name: "y",
        label: "Y",
        value: String(tileY),
        type: "number",
        required: true,
        group: "placement",
      },
      {
        type: "context",
        text: "Spawns a new object or agent at the chosen position. A new entity id is always generated.",
        group: "basic",
      },
    ],
    null,
    {
      actions: [
        {
          label: "Load from template",
          onSubmit: async (data) => {
            if (!data.templateId) {
              throw new Error(
                "No templates saved yet. Right-click an object or agent and choose Save as…",
              );
            }
            const result = await postSpawnEntityTemplate(data.templateId, {
              position: [Number(data.x), Number(data.y)],
              areaId,
            });
            showToast(result.message || "Template loaded.", false);
            await onStateChanged(result.snapshot);
          },
        },
        {
          label: "Load from file",
          onSubmit: async (data) => {
            let picked;
            try {
              picked = await pickJsonFile();
            } catch {
              throw new Error("Invalid JSON file.");
            }
            if (!picked) return false;
            const result = await postSpawnEntityFromTemplate(picked.template, {
              position: [Number(data.x), Number(data.y)],
              areaId,
            });
            showToast(result.message || "Loaded from file.", false);
            await onStateChanged(result.snapshot);
          },
        },
      ],
    },
  );
}

export function openSaveAreaTemplateModal() {
  const snap = normalizeSnapshot(getSnapshot());
  const areaId = snap?.active_area_id;
  if (!areaId) {
    showToast("No active area selected.", true);
    return;
  }
  const defaultName = `${slugifyTemplateFilename(areaId)}.json`;
  openModal(
    "Save area as template",
    [
      {
        name: "filename",
        label: "Filename",
        value: defaultName,
        required: true,
        group: "basic",
      },
      {
        name: "name",
        label: "Template name",
        value: areaId,
        required: true,
        group: "basic",
      },
      {
        name: "includeHiddenObjects",
        label: "Include hidden objects",
        type: "checkbox",
        value: true,
        group: "basic",
      },
      {
        type: "context",
        text: "Area templates include grid bounds, decorations, and objects with positions. Agents are not saved. Entity ids are regenerated on load.",
        group: "basic",
      },
    ],
    null,
    {
      actions: [
        {
          label: "Save as template",
          onSubmit: async (data) => {
            const result = await postSaveAreaTemplate({
              areaId,
              filename: data.filename,
              name: data.name,
              includeHiddenObjects: Boolean(data.includeHiddenObjects),
            });
            showToast(result.message || "Area template saved.", false);
            const { refreshTemplatesList } = await import("./templates.js");
            await refreshTemplatesList();
          },
        },
        {
          label: "Save as file",
          onSubmit: async (data) => {
            const { filename } = await downloadAreaTemplateFromArea({
              areaId,
              filename: data.filename,
              name: data.name,
              includeHiddenObjects: Boolean(data.includeHiddenObjects),
            });
            showToast(`Saved ${filename}`, false);
          },
        },
      ],
    },
  );
}

export async function openLoadAreaTemplateModal() {
  let templates = [];
  try {
    const data = await fetchAreaTemplates();
    templates = data.templates || [];
  } catch (err) {
    showToast(String(err.message || err), true);
    return;
  }

  const snap = normalizeSnapshot(getSnapshot());
  const activeAreaId = snap?.active_area_id ?? DEFAULT_AREA_ID;
  const templateOptions = templates.length
    ? templates.map((item) => ({
        value: item.id,
        label: `${item.name} (${item.grid_width ?? "?"}×${item.grid_height ?? "?"})`,
      }))
    : [{ value: "", label: "No area templates saved", disabled: true }];

  openModal(
    "Load area template",
    [
      {
        name: "templateId",
        label: "Studio template",
        type: "select",
        value: templates[0]?.id ?? "",
        options: templateOptions,
        group: "basic",
      },
      {
        name: "mode",
        label: "Load mode",
        type: "select",
        value: "new",
        options: [
          { value: "new", label: "Create new area" },
          { value: "replace", label: "Replace current area contents" },
        ],
        group: "basic",
      },
      {
        name: "areaId",
        label: "Target area id",
        value: "new_area",
        required: true,
        group: "basic",
      },
      {
        type: "context",
        text: "Replace mode overwrites decorations and objects in the target area. Agents in that area are kept. Confirm before loading.",
        group: "basic",
      },
    ],
    null,
    {
      actions: [
        {
          label: "Load from template",
          onSubmit: async (data) => {
            if (!data.templateId) {
              throw new Error("No area templates saved yet. Use Save area… first.");
            }
            const mode = data.mode === "replace" ? "replace" : "new";
            const targetAreaId =
              mode === "replace"
                ? activeAreaId
                : String(data.areaId || "")
                    .trim()
                    .toLowerCase();
            if (!targetAreaId) {
              throw new Error("Target area id is required.");
            }
            if (
              mode === "replace" &&
              !window.confirm(`Replace all contents of area "${targetAreaId}" with this template?`)
            ) {
              return false;
            }
            const result = await postSpawnAreaTemplate(data.templateId, {
              areaId: targetAreaId,
              mode,
            });
            showToast(result.message || "Area template loaded.", false);
            await onStateChanged(result.snapshot);
          },
        },
        {
          label: "Load from file",
          onSubmit: async (data) => {
            let picked;
            try {
              picked = await pickJsonFile();
            } catch {
              throw new Error("Invalid JSON file.");
            }
            if (!picked) return false;
            const mode = data.mode === "replace" ? "replace" : "new";
            const targetAreaId =
              mode === "replace"
                ? activeAreaId
                : String(data.areaId || "")
                    .trim()
                    .toLowerCase();
            if (!targetAreaId) {
              throw new Error("Target area id is required.");
            }
            if (
              mode === "replace" &&
              !window.confirm(`Replace all contents of area "${targetAreaId}" with this template?`)
            ) {
              return false;
            }
            const result = await postSpawnAreaFromTemplate(picked.template, {
              areaId: targetAreaId,
              mode,
            });
            showToast(result.message || "Area template loaded.", false);
            await onStateChanged(result.snapshot);
          },
        },
      ],
    },
  );
}

export { showToast };
