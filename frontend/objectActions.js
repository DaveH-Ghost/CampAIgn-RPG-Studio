/**
 * Manage object actions modal (V0.4.0e / V0.6.1 handlers).
 */

import {
  buildAddObjectAction,
  buildRemoveObjectAction,
  fetchInteractionHandlers,
  postCommand,
} from "./api.js";
import { normalizeSnapshot } from "./snapshot.js";
import { attachTemplateVarHelp } from "./templateVarsHelp.js";

const FALLBACK_HANDLER_CHOICES = [
  { id: "none", label: "None" },
  { id: "delete_self", label: "delete_self — remove object" },
  { id: "random_move_self", label: "random_move_self — move object randomly" },
  { id: "move_area", label: "move_area — transfer agent to another area" },
];

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

let handlerChoicesCache = null;

export function clearHandlerChoicesCache() {
  handlerChoicesCache = null;
}

async function getHandlerChoices() {
  if (handlerChoicesCache) return handlerChoicesCache;
  try {
    const data = await fetchInteractionHandlers();
    const handlers = data?.handlers || [];
    handlerChoicesCache = [
      { id: "none", label: "None" },
      ...handlers.map((h) => ({
        id: h.id,
        label: h.description ? `${h.id} — ${h.description}` : h.id,
      })),
    ];
  } catch {
    handlerChoicesCache = FALLBACK_HANDLER_CHOICES;
  }
  return handlerChoicesCache;
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
  const handlerId = action?.handler_id;
  if (!handlerId) return "no handler";
  if (handlerId === "move_area") {
    const area = action.handler_params?.["dest-area"] || "?";
    const at = action.handler_params?.["dest-at"] || "?";
    return `move_area → ${area} (${at})`;
  }
  return handlerId;
}

function formatActionSummary(action) {
  const kind = action?.kind || "interact";
  const kindLabel = kind === "trigger" ? "trigger" : "interact";
  let suffix = formatHandlerSummary(action);
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

function showManageModal() {
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
  modalBackdrop.classList.remove("hidden");
}

export function openManageObjectActionsModal(entity) {
  manageObject = entity;
  showManageModal();
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

function parseHandlerFromAction(action) {
  const handlerId = action?.handler_id;
  if (!handlerId) {
    return { handler: "none", destArea: "", destX: "0", destY: "0" };
  }
  if (handlerId === "move_area") {
    const parts = String(action.handler_params?.["dest-at"] || "0,0").split(",");
    return {
      handler: "move_area",
      destArea: action.handler_params?.["dest-area"] || "",
      destX: (parts[0] || "0").trim(),
      destY: (parts[1] || "0").trim(),
    };
  }
  return { handler: handlerId, destArea: "", destX: "0", destY: "0" };
}

async function openActionForm(existingName, existingAction) {
  const isEdit = existingName != null;
  const parsed = isEdit
    ? parseHandlerFromAction(existingAction)
    : { handler: "none", destArea: "", destX: "0", destY: "0" };
  const areas = listAreaIds();
  const defaultDestArea = parsed.destArea || areas[0] || "room";
  const handlerChoices = await getHandlerChoices();

  const actionKind = existingAction?.kind || "interact";

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
      value: existingAction?.result ?? (actionKind === "trigger" ? "(trigger)" : "You interact with it."),
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
        (actionKind === "trigger"
          ? "{actor} triggers it."
          : "{actor} interacts with it."),
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
    if (choice.id === parsed.handler) opt.selected = true;
    handlerSelect.appendChild(opt);
  }
  handlerWrap.appendChild(handlerSelect);
  modalForm.appendChild(handlerWrap);

  const moveFields = document.createElement("div");
  moveFields.className = "action-move-fields";

  const destAreaWrap = document.createElement("label");
  destAreaWrap.className = "modal-field";
  const destAreaLabel = document.createElement("span");
  destAreaLabel.textContent = "Destination area";
  destAreaWrap.appendChild(destAreaLabel);
  const destAreaSelect = document.createElement("select");
  destAreaSelect.name = "destArea";
  for (const areaId of areas) {
    const opt = document.createElement("option");
    opt.value = areaId;
    opt.textContent = areaId;
    if (areaId === defaultDestArea) opt.selected = true;
    destAreaSelect.appendChild(opt);
  }
  destAreaWrap.appendChild(destAreaSelect);
  moveFields.appendChild(destAreaWrap);

  const destRow = document.createElement("div");
  destRow.className = "action-dest-row";

  const destXWrap = document.createElement("label");
  destXWrap.className = "modal-field action-dest-coord";
  const destXLabel = document.createElement("span");
  destXLabel.textContent = "Dest X";
  destXWrap.appendChild(destXLabel);
  const destXInput = document.createElement("input");
  destXInput.type = "number";
  destXInput.name = "destX";
  destXInput.value = parsed.destX;
  destXWrap.appendChild(destXInput);
  destRow.appendChild(destXWrap);

  const destYWrap = document.createElement("label");
  destYWrap.className = "modal-field action-dest-coord";
  const destYLabel = document.createElement("span");
  destYLabel.textContent = "Dest Y";
  destYWrap.appendChild(destYLabel);
  const destYInput = document.createElement("input");
  destYInput.type = "number";
  destYInput.name = "destY";
  destYInput.value = parsed.destY;
  destYWrap.appendChild(destYInput);
  destRow.appendChild(destYWrap);

  moveFields.appendChild(destRow);
  modalForm.appendChild(moveFields);

  const toggleMoveFields = () => {
    moveFields.classList.toggle("hidden", handlerSelect.value !== "move_area");
  };
  const syncKindFields = () => {
    const isTrigger = kindSelect.value === "trigger";
    triggerFields.classList.toggle("hidden", !isTrigger);
    for (const wrap of modalForm.querySelectorAll(".modal-field-conditional")) {
      const allowed = (wrap.dataset.showWhenValues || "")
        .split(",")
        .map((v) => v.trim());
      const current = kindSelect.value;
      wrap.hidden = !allowed.includes(String(current));
    }
    toggleMoveFields();
  };
  handlerSelect.addEventListener("change", syncKindFields);
  kindSelect.addEventListener("change", syncKindFields);
  syncKindFields();

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
    const data = {
      name: modalForm.elements.name.value.trim(),
      range: modalForm.elements.range.value.trim(),
      kind: modalForm.elements.kind.value,
      result: modalForm.elements.result?.value?.trim() || "(trigger)",
      passive: modalForm.elements.passive.value.trim(),
      handler: modalForm.elements.handler?.value || "none",
      destArea: modalForm.elements.destArea?.value,
      destX: modalForm.elements.destX?.value?.trim(),
      destY: modalForm.elements.destY?.value?.trim(),
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
          haltMovement: data.kind === "trigger" ? data.haltMovement : undefined,
          deleteAfterTrigger: data.kind === "trigger" ? data.deleteAfterTrigger : undefined,
          triggerExceptions: data.kind === "trigger" ? data.triggerExceptions : undefined,
          handler: data.handler,
          destArea: data.destArea,
          destX: data.destX,
          destY: data.destY,
        }),
      );
      await refreshManagedObject();
      showManageModal();
    } catch (err) {
      modalError.textContent = String(err.message || err);
    }
  };
}
