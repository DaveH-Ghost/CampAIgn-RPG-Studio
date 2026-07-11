/**
 * Inline player turn form (1.1.0) and shared field defs for manual compound turns.
 */

import { buildCompoundTurnPayload } from "./api.js";
import { asArray, normalizeSnapshot } from "./snapshot.js";

export function playerTurnFieldDefs(coordinateMode = "full") {
  const relative = coordinateMode === "relative";
  return [
    {
      name: "reasoning",
      label: "Reasoning",
      value: "Manual test turn.",
      type: "textarea",
      rows: 2,
      required: true,
    },
    {
      name: "move",
      label: relative
        ? "Move (obj_*, agent_*, or blank)"
        : "Move (x,y, obj_*, agent_*, or blank)",
      value: "",
      placeholder: relative ? "obj_ball_01" : "4,4",
    },
    {
      name: "look",
      label: "Look target (entity id)",
      value: "",
      placeholder: "obj_ball_01",
    },
    {
      name: "say",
      label: "Say (dialogue)",
      value: "",
      type: "textarea",
      rows: 2,
    },
    {
      name: "action",
      label: "Turn action",
      type: "select",
      value: "none",
      options: [
        { value: "none", label: "none" },
        { value: "interact", label: "interact" },
        { value: "emote", label: "emote" },
      ],
    },
    {
      name: "target",
      label: "Target (interact / emote)",
      value: "",
      showWhen: { field: "action", values: ["interact", "emote"] },
    },
    {
      name: "verb",
      label: "Verb / action name",
      value: "",
      showWhen: { field: "action", values: ["interact", "emote"] },
    },
  ];
}

function readPanelForm(panelEl) {
  const data = {};
  for (const el of panelEl.querySelectorAll("[name]")) {
    if (el.type === "checkbox") {
      data[el.name] = el.checked;
    } else {
      data[el.name] = el.value;
    }
  }
  return data;
}

function validatePlayerTurnData(data) {
  const action = data.action || "none";
  if (
    (action === "interact" || action === "emote")
    && (!String(data.target ?? "").trim() || !String(data.verb ?? "").trim())
  ) {
    return "Interact and emote turns require target and verb.";
  }
  if (!String(data.reasoning ?? "").trim()) {
    return "Reasoning is required.";
  }
  return null;
}

function syncActionFieldVisibility(panelEl) {
  const action = panelEl.querySelector('[name="action"]')?.value ?? "none";
  const show = action === "interact" || action === "emote";
  const extra = panelEl.querySelector("#player-turn-action-extra");
  if (extra) {
    extra.classList.toggle("hidden", !show);
  }
}

function updateMoveHints(panelEl, coordinateMode) {
  const relative = coordinateMode === "relative";
  const moveInput = panelEl.querySelector('[name="move"]');
  const moveLabel = panelEl.querySelector("#player-turn-move-label");
  if (moveInput) {
    moveInput.placeholder = relative ? "obj_ball_01" : "4,4";
  }
  if (moveLabel) {
    moveLabel.textContent = relative
      ? "Move (obj_*, agent_*, or blank)"
      : "Move (x,y, obj_*, agent_*, or blank)";
  }
}

let panelEl;
let headingEl;
let submitBtn;
let getSnapshot = () => null;
let getCoordinateMode = () => "full";
let onSubmit = async () => {};
let showToast = () => {};

export function initPlayerTurnPanel({
  panelFormEl,
  headingEl: heading,
  submitBtnEl,
  getSnapshotFn,
  getCoordinateModeFn,
  onSubmitFn,
  showToastFn,
}) {
  panelEl = panelFormEl;
  headingEl = heading;
  submitBtn = submitBtnEl;
  getSnapshot = getSnapshotFn ?? getSnapshot;
  getCoordinateMode = getCoordinateModeFn ?? getCoordinateMode;
  onSubmit = onSubmitFn ?? onSubmit;
  showToast = showToastFn ?? showToast;

  const actionSelect = panelEl.querySelector('[name="action"]');
  actionSelect?.addEventListener("change", () => syncActionFieldVisibility(panelEl));

  panelEl.addEventListener("submit", async (e) => {
    e.preventDefault();
    const data = readPanelForm(panelEl);
    const err = validatePlayerTurnData(data);
    if (err) {
      showToast(err, true);
      return;
    }
    try {
      await onSubmit(buildCompoundTurnPayload(data));
    } catch (error) {
      showToast(String(error.message || error), true);
    }
  });
}

export function syncPlayerTurnPanel(snapshot) {
  if (!panelEl) return;
  const snap = normalizeSnapshot(snapshot ?? getSnapshot());
  const active = asArray(snap?.agents).find((agent) => agent.id === snap?.active_agent_id);
  const coordinateMode = getCoordinateMode();

  updateMoveHints(panelEl, coordinateMode);
  syncActionFieldVisibility(panelEl);

  if (active?.is_player) {
    panelEl.classList.remove("hidden");
    if (headingEl) {
      headingEl.textContent = `Player turn — ${active.name}`;
    }
  } else {
    panelEl.classList.add("hidden");
  }
}

export function setPlayerTurnPanelBusy(busy) {
  if (!panelEl) return;
  panelEl.querySelectorAll("input, textarea, select, button").forEach((el) => {
    el.disabled = busy;
  });
}

export function buildPlayerTurnPayloadFromPanel() {
  if (!panelEl) {
    throw new Error("Player turn panel is not initialized.");
  }
  const data = readPanelForm(panelEl);
  const err = validatePlayerTurnData(data);
  if (err) {
    throw new Error(err);
  }
  return buildCompoundTurnPayload(data);
}

export { validatePlayerTurnData, readPanelForm as readPlayerTurnFormData };
