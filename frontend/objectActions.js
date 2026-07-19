/**
 * Manage object actions modal (V0.4.0e / V0.6.1 handlers / 1.4.2 param_fields).
 */

import {
  buildAddObjectAction,
  buildRemoveObjectAction,
  fetchEntityTemplates,
  fetchInteractionHandlers,
  postCommand,
} from "./api.js";
import {
  collectHandlerParams,
  formatHandlerSummaryFromCatalog,
  renderParamFields,
} from "./handlerParamSchema.js";
import { normalizeSnapshot } from "./snapshot.js";
import { attachTemplateVarHelp } from "./templateVarsHelp.js";

const FALLBACK_HANDLER_CHOICES = [{ id: "none", label: "None" }];

let getSnapshot = () => null;
let onStateChanged = async () => {};
let showToast = () => {};
let modalTitle;
let modalForm;
let modalError;
let modalBackdrop;
let closeModal;

/** @type {{ id: string, name: string, actions?: string[], actions_detail?: Record<string, object> } | null} */
let manageObject = null;

/** @type {Record<string, object> | null} */
let handlerCatalogById = null;
/** @type {{ id: string, label: string }[] | null} */
let handlerChoicesCache = null;
/** @type {{ id: string, kind?: string, name?: string }[] | null} */
let entityTemplatesCache = null;

export function clearHandlerChoicesCache() {
  handlerChoicesCache = null;
  handlerCatalogById = null;
  entityTemplatesCache = null;
}

async function getHandlerCatalogById() {
  if (handlerCatalogById) return handlerCatalogById;
  await getHandlerChoices();
  return handlerCatalogById || {};
}

async function getHandlerChoices() {
  if (handlerChoicesCache) return handlerChoicesCache;
  try {
    const data = await fetchInteractionHandlers();
    const handlers = data?.handlers || [];
    handlerCatalogById = Object.fromEntries(handlers.map((h) => [h.id, h]));
    handlerChoicesCache = [
      { id: "none", label: "None" },
      ...handlers.map((h) => ({
        id: h.id,
        label: h.description ? `${h.id} — ${h.description}` : h.id,
      })),
    ];
  } catch {
    handlerCatalogById = {};
    handlerChoicesCache = FALLBACK_HANDLER_CHOICES;
  }
  return handlerChoicesCache;
}

async function getEntityTemplateChoices({ force = false } = {}) {
  if (!force && entityTemplatesCache) return entityTemplatesCache;
  try {
    const data = await fetchEntityTemplates();
    entityTemplatesCache = data?.templates || [];
  } catch {
    entityTemplatesCache = [];
  }
  return entityTemplatesCache;
}

export function initObjectActions(deps) {
  getSnapshot = deps.getSnapshotFn;
  onStateChanged = deps.onStateChangedFn;
  showToast = deps.showToastFn;
  modalTitle = deps.modalTitleEl;
  modalForm = deps.modalFormEl;
  modalError = deps.modalErrorEl;
  modalBackdrop = deps.modalBackdropEl;
  closeModal = deps.closeModal;
}

function listAreaIds() {
  const snap = normalizeSnapshot(getSnapshot());
  if (!snap?.areas) return [];
  return Object.keys(snap.areas).sort();
}

function formatHandlerSummary(action) {
  return formatHandlerSummaryFromCatalog(action, handlerCatalogById || {});
}

function formatActionSummary(action) {
  const kind = action?.kind || "interact";
  const kindLabel = kind === "trigger" ? "trigger" : "interact";
  let suffix = formatHandlerSummary(action);
  if (action?.enabled === false) {
    suffix += " · hidden";
  }
  if (kind === "trigger") {
    const flags = [];
    if (action?.halt_movement) flags.push("halt");
    if (action?.delete_after_trigger === false) flags.push("reusable");
    if (flags.length) suffix += ` · ${flags.join(", ")}`;
  }
  return `${kindLabel} · ${suffix}`;
}

function actionNames() {
  const detail = manageObject?.actions_detail || {};
  if (manageObject?.actions?.length) {
    return [...manageObject.actions].sort();
  }
  return Object.keys(detail).sort();
}

async function refreshManagedObject() {
  const snap = normalizeSnapshot(getSnapshot());
  for (const block of Object.values(snap?.areas || {})) {
    const found = (block.objects || []).find((o) => o.id === manageObject?.id);
    if (found) {
      manageObject = found;
      return;
    }
  }
}

async function runCommand(line) {
  const result = await postCommand(line);
  if (!result.ok) throw new Error(result.message);
  showToast(result.message, false);
  if (result.snapshot) {
    await onStateChanged(result.snapshot);
  } else {
    await onStateChanged();
  }
}

function setActionModalWide(wide) {
  modalBackdrop?.querySelector(".modal")?.classList.toggle("modal--wide", Boolean(wide));
}

function showManageModal() {
  setActionModalWide(true);
  modalTitle.textContent = `Manage actions — ${manageObject.name}`;
  modalForm.innerHTML = "";
  modalError.textContent = "";

  const detail = manageObject?.actions_detail || {};
  const names = actionNames();

  if (names.length === 0) {
    const empty = document.createElement("p");
    empty.className = "modal-hint";
    empty.textContent = "No actions yet. Add one below.";
    modalForm.appendChild(empty);
  } else {
    const list = document.createElement("ul");
    list.className = "action-list";
    for (const name of names) {
      const action = detail[name] || {};
      const li = document.createElement("li");
      li.className = "action-list-item";
      const summary = document.createElement("span");
      summary.textContent = `${name} — ${formatActionSummary(action)}`;
      li.appendChild(summary);

      const buttons = document.createElement("span");
      buttons.className = "action-list-buttons";
      const editBtn = document.createElement("button");
      editBtn.type = "button";
      editBtn.textContent = "Edit";
      editBtn.addEventListener("click", () => openActionForm(name, action));
      const removeBtn = document.createElement("button");
      removeBtn.type = "button";
      removeBtn.textContent = "Remove";
      removeBtn.addEventListener("click", () => removeAction(name));
      buttons.appendChild(editBtn);
      buttons.appendChild(removeBtn);
      li.appendChild(buttons);
      list.appendChild(li);
    }
    modalForm.appendChild(list);
  }

  const actions = document.createElement("div");
  actions.className = "modal-actions";

  const addBtn = document.createElement("button");
  addBtn.type = "button";
  addBtn.textContent = "Add action…";
  addBtn.addEventListener("click", () => openActionForm(null, null));
  actions.appendChild(addBtn);
  modalForm.appendChild(actions);

  modalForm.onsubmit = (e) => e.preventDefault();
  modalBackdrop.classList.remove("hidden");
}

export function openManageObjectActionsModal(entity) {
  manageObject = entity;
  void getHandlerChoices().then(() => showManageModal());
}

async function removeAction(name) {
  if (!window.confirm(`Remove action "${name}" from ${manageObject.name}?`)) return;
  try {
    await runCommand(buildRemoveObjectAction(manageObject.id, name));
    await refreshManagedObject();
    showManageModal();
  } catch (err) {
    modalError.textContent = String(err.message || err);
  }
}

async function openActionForm(existingName, existingAction) {
  const isEdit = existingName != null;
  const areas = listAreaIds();
  const handlerChoices = await getHandlerChoices();
  const catalogById = await getHandlerCatalogById();
  const templates = await getEntityTemplateChoices({ force: true });
  const actionKind = existingAction?.kind || "interact";
  const initialHandler = existingAction?.handler_id || "none";
  const initialParams = { ...(existingAction?.handler_params || {}) };

  setActionModalWide(true);
  modalTitle.textContent = isEdit
    ? `Edit action — ${existingName}`
    : `Add action — ${manageObject.name}`;
  modalForm.innerHTML = "";
  modalError.textContent = "";

  const kindWrap = document.createElement("label");
  kindWrap.className = "modal-field";
  const kindLabel = document.createElement("span");
  kindLabel.textContent = "Kind";
  kindWrap.appendChild(kindLabel);
  const kindSelect = document.createElement("select");
  kindSelect.name = "kind";
  for (const choice of [
    { id: "interact", label: "interact — LLM compound-turn action" },
    { id: "trigger", label: "trigger — fires on path step (area event)" },
  ]) {
    const opt = document.createElement("option");
    opt.value = choice.id;
    opt.textContent = choice.label;
    if (choice.id === actionKind) opt.selected = true;
    kindSelect.appendChild(opt);
  }
  kindWrap.appendChild(kindSelect);
  modalForm.appendChild(kindWrap);

  const fields = [
    {
      name: "name",
      label: "Action name",
      value: existingName ?? "enter",
      required: true,
    },
    {
      name: "range",
      label: "Range (Chebyshev tiles)",
      value: String(existingAction?.range ?? (actionKind === "trigger" ? 0 : 1)),
      type: "number",
      required: true,
    },
    {
      name: "result",
      label: "Result (agent sees)",
      value:
        existingAction?.result ??
        (actionKind === "trigger" ? "(trigger)" : "You interact with it."),
      type: "textarea",
      required: true,
      templateHelp: true,
      interactOnly: true,
    },
    {
      name: "passive",
      label: "Passive / area event text",
      value:
        existingAction?.passive_result ??
        (actionKind === "trigger" ? "{actor} triggers it." : "{actor} interacts with it."),
      type: "textarea",
      required: true,
      templateHelp: true,
    },
  ];

  for (const field of fields) {
    const wrap = document.createElement("label");
    wrap.className = "modal-field";
    if (field.interactOnly) {
      wrap.classList.add("modal-field-conditional");
      wrap.dataset.showWhenField = "kind";
      wrap.dataset.showWhenValues = "interact";
    }
    const label = document.createElement("span");
    label.className = "modal-field-label-row";
    label.textContent = field.label;
    if (field.templateHelp) attachTemplateVarHelp(label);
    wrap.appendChild(label);

    let input;
    if (field.type === "textarea") {
      input = document.createElement("textarea");
      input.rows = 2;
      input.value = field.value ?? "";
    } else {
      input = document.createElement("input");
      input.type = field.type || "text";
      input.value = field.value ?? "";
    }
    input.name = field.name;
    if (field.required) input.required = true;
    wrap.appendChild(input);
    modalForm.appendChild(wrap);
  }

  const triggerFields = document.createElement("div");
  triggerFields.className = "action-trigger-fields";

  const haltWrap = document.createElement("label");
  haltWrap.className = "modal-field";
  const haltLabel = document.createElement("span");
  haltLabel.textContent = "Halt movement on trigger";
  haltWrap.appendChild(haltLabel);
  const haltInput = document.createElement("input");
  haltInput.type = "checkbox";
  haltInput.name = "haltMovement";
  haltInput.checked = existingAction?.halt_movement ?? true;
  haltWrap.appendChild(haltInput);
  triggerFields.appendChild(haltWrap);

  const deleteWrap = document.createElement("label");
  deleteWrap.className = "modal-field";
  const deleteLabel = document.createElement("span");
  deleteLabel.textContent = "Delete object after trigger";
  deleteWrap.appendChild(deleteLabel);
  const deleteInput = document.createElement("input");
  deleteInput.type = "checkbox";
  deleteInput.name = "deleteAfterTrigger";
  deleteInput.checked = existingAction?.delete_after_trigger !== false;
  deleteWrap.appendChild(deleteInput);
  triggerFields.appendChild(deleteWrap);

  const exceptionsWrap = document.createElement("label");
  exceptionsWrap.className = "modal-field";
  const exceptionsLabel = document.createElement("span");
  exceptionsLabel.textContent = "Trigger exceptions (agent ids)";
  exceptionsWrap.appendChild(exceptionsLabel);
  const exceptionsInput = document.createElement("input");
  exceptionsInput.type = "text";
  exceptionsInput.name = "triggerExceptions";
  exceptionsInput.value = (existingAction?.trigger_exceptions || []).join(", ");
  exceptionsWrap.appendChild(exceptionsInput);
  triggerFields.appendChild(exceptionsWrap);

  modalForm.appendChild(triggerFields);

  const enabledWrap = document.createElement("label");
  enabledWrap.className = "modal-field";
  const enabledLabel = document.createElement("span");
  enabledLabel.textContent = "Enabled (visible / usable)";
  enabledWrap.appendChild(enabledLabel);
  const enabledInput = document.createElement("input");
  enabledInput.type = "checkbox";
  enabledInput.name = "enabled";
  enabledInput.checked = existingAction?.enabled !== false;
  enabledWrap.appendChild(enabledInput);
  modalForm.appendChild(enabledWrap);

  const handlerWrap = document.createElement("label");
  handlerWrap.className = "modal-field";
  const handlerLabel = document.createElement("span");
  handlerLabel.textContent = "Handler";
  handlerWrap.appendChild(handlerLabel);
  const handlerSelect = document.createElement("select");
  handlerSelect.name = "handler";
  for (const choice of handlerChoices) {
    const opt = document.createElement("option");
    opt.value = choice.id;
    opt.textContent = choice.label;
    if (choice.id === initialHandler) opt.selected = true;
    handlerSelect.appendChild(opt);
  }
  handlerWrap.appendChild(handlerSelect);
  modalForm.appendChild(handlerWrap);

  const paramHost = document.createElement("div");
  paramHost.className = "action-handler-params";
  modalForm.appendChild(paramHost);

  const syncParamFields = () => {
    paramHost.innerHTML = "";
    const handlerId = handlerSelect.value;
    if (!handlerId || handlerId === "none") return;
    const entry = catalogById[handlerId];
    const paramFields = entry?.param_fields || [];
    if (!paramFields.length) return;
    renderParamFields(paramHost, paramFields, {
      params: initialParams,
      areas,
      templates,
      catalogById,
      attachTemplateHelp: attachTemplateVarHelp,
      parentHandlerId: handlerId,
    });
  };

  const syncKindFields = () => {
    const isTrigger = kindSelect.value === "trigger";
    triggerFields.classList.toggle("hidden", !isTrigger);
    for (const wrap of modalForm.querySelectorAll(".modal-field-conditional")) {
      const allowed = (wrap.dataset.showWhenValues || "").split(",").map((v) => v.trim());
      const current = kindSelect.value;
      wrap.hidden = !allowed.includes(String(current));
    }
  };
  handlerSelect.addEventListener("change", syncParamFields);
  kindSelect.addEventListener("change", syncKindFields);
  syncKindFields();
  syncParamFields();

  const actions = document.createElement("div");
  actions.className = "modal-actions";

  const backBtn = document.createElement("button");
  backBtn.type = "button";
  backBtn.textContent = "Back";
  backBtn.addEventListener("click", () => showManageModal());

  const submit = document.createElement("button");
  submit.type = "submit";
  submit.textContent = isEdit ? "Save" : "Add";

  actions.appendChild(backBtn);
  actions.appendChild(submit);
  modalForm.appendChild(actions);

  modalForm.onsubmit = async (e) => {
    e.preventDefault();
    modalError.textContent = "";
    const handlerId = modalForm.elements.handler?.value || "none";
    const entry = catalogById[handlerId];
    const handlerParams =
      handlerId && handlerId !== "none"
        ? collectHandlerParams(modalForm, entry?.param_fields || [], catalogById)
        : {};
    const data = {
      name: modalForm.elements.name.value.trim(),
      range: modalForm.elements.range.value.trim(),
      kind: modalForm.elements.kind.value,
      result: modalForm.elements.result?.value?.trim() || "(trigger)",
      passive: modalForm.elements.passive.value.trim(),
      handler: handlerId,
      handlerParams,
      enabled: modalForm.elements.enabled?.checked !== false,
      haltMovement: modalForm.elements.haltMovement?.checked ?? true,
      deleteAfterTrigger: modalForm.elements.deleteAfterTrigger?.checked ?? true,
      triggerExceptions: modalForm.elements.triggerExceptions?.value?.trim() ?? "",
    };
    if (!data.name) {
      modalError.textContent = "Action name is required.";
      return;
    }
    try {
      if (isEdit) {
        await runCommand(buildRemoveObjectAction(manageObject.id, existingName));
      }
      await runCommand(
        buildAddObjectAction(manageObject.id, {
          name: data.name,
          range: data.range,
          result: data.result,
          passive: data.passive,
          kind: data.kind,
          enabled: data.enabled,
          haltMovement: data.kind === "trigger" ? data.haltMovement : undefined,
          deleteAfterTrigger: data.kind === "trigger" ? data.deleteAfterTrigger : undefined,
          triggerExceptions: data.kind === "trigger" ? data.triggerExceptions : undefined,
          handler: data.handler,
          handlerParams: data.handlerParams,
        }),
      );
      await refreshManagedObject();
      showManageModal();
    } catch (err) {
      modalError.textContent = String(err.message || err);
    }
  };
}
