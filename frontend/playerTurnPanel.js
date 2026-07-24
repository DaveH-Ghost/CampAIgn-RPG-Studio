/**
 * Inline player turn form (1.1.0) and shared field defs for manual compound turns.
 * Verb/target filtering uses GET /api/player-turn-assist (1.4.2).
 */

import { buildCompoundTurnPayload, fetchPlayerTurnAssist, fetchTurnVerbs } from "./api.js";
import { asArray, normalizeSnapshot } from "./snapshot.js";

/** @type {{ id: string, description?: string }[]} */
let turnVerbCatalog = [];

/** @type {{ id: string, label?: string, verbs: string[] }[]} */
let assistTargets = [];

export function playerTurnFieldDefs(coordinateMode = "full") {
  const relative = coordinateMode === "relative";
  const turnVerbOptions = [
    { value: "", label: "(select turn verb)" },
    ...turnVerbCatalog.map((verb) => ({
      value: verb.id,
      label: verb.description ? `${verb.id} — ${verb.description}` : verb.id,
    })),
  ];
  return [
    {
      name: "reasoning",
      label: "Reasoning",
      value: "Looking around.",
      type: "textarea",
      rows: 2,
      required: true,
    },
    {
      name: "move",
      label: relative ? "Move (obj_*, agent_*, or blank)" : "Move (x,y, obj_*, agent_*, or blank)",
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
        { value: "verb", label: "verb" },
      ],
    },
    {
      name: "target",
      label: "Target (required for interact; optional for emote / verb)",
      value: "",
      showWhen: { field: "action", values: ["interact", "emote", "verb"] },
    },
    {
      name: "verb",
      label: "Verb / action name",
      value: "",
      showWhen: { field: "action", values: ["interact", "emote"] },
    },
    {
      name: "turn_verb",
      label: "Registered turn verb",
      type: "select",
      value: "",
      options: turnVerbOptions,
      showWhen: { field: "action", values: ["verb"] },
    },
  ];
}

function assistRowForTarget(targetId) {
  const cleaned = String(targetId || "").trim();
  if (!cleaned) return null;
  return assistTargets.find((row) => row.id === cleaned) || null;
}

function verbsForTurnDropdown(targetItemId) {
  const row = assistRowForTarget(targetItemId);
  if (!row) return turnVerbCatalog;
  const allowed = new Set(row.verbs || []);
  return turnVerbCatalog.filter((verb) => allowed.has(verb.id));
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
  const action = data.action || "none";
  if (action === "verb") {
    const verbSelect = panelEl.querySelector("#player-turn-verb-select");
    data.verb = verbSelect?.value ?? "";
  }
  return data;
}

function validatePlayerTurnData(data) {
  const action = data.action || "none";
  if (
    action === "interact" &&
    (!String(data.target ?? "").trim() || !String(data.verb ?? "").trim())
  ) {
    return "Interact turns require target and verb.";
  }
  if (action === "emote" && !String(data.verb ?? "").trim()) {
    return "Emote turns require a verb (target is optional).";
  }
  if (action === "verb" && !String(data.verb ?? "").trim()) {
    return "Verb turns require a registered turn verb.";
  }
  if (!String(data.reasoning ?? "").trim()) {
    return "Reasoning is required.";
  }
  return null;
}

function populateTurnVerbSelect(panelEl) {
  const select = panelEl.querySelector("#player-turn-verb-select");
  if (!select) return;
  const previous = select.value;
  const targetId = panelEl.querySelector('[name="target"]')?.value ?? "";
  const verbs = verbsForTurnDropdown(targetId);
  select.innerHTML = "";
  const blank = document.createElement("option");
  blank.value = "";
  blank.textContent = "(select turn verb)";
  select.appendChild(blank);
  for (const verb of verbs) {
    const option = document.createElement("option");
    option.value = verb.id;
    option.textContent = verb.description ? `${verb.id} — ${verb.description}` : verb.id;
    select.appendChild(option);
  }
  if (previous && [...select.options].some((opt) => opt.value === previous)) {
    select.value = previous;
  } else if (verbs.length === 1) {
    select.value = verbs[0].id;
  }
}

function prefillAssistVerbTurn(panelEl) {
  const action = panelEl.querySelector('[name="action"]')?.value ?? "none";
  if (action !== "verb") return;

  const targetInput = panelEl.querySelector('[name="target"]');
  if (targetInput && !String(targetInput.value || "").trim() && assistTargets.length === 1) {
    targetInput.value = assistTargets[0].id || "";
  }

  const targetId = targetInput?.value ?? "";
  const row = assistRowForTarget(targetId);
  if (!row) return;

  const preferred = (row.verbs || []).filter((name) => name !== "drop");
  const select = panelEl.querySelector("#player-turn-verb-select");
  if (!select || select.value || preferred.length !== 1) return;
  if ([...select.options].some((opt) => opt.value === preferred[0])) {
    select.value = preferred[0];
  }
}

function syncActionFieldVisibility(panelEl) {
  const action = panelEl.querySelector('[name="action"]')?.value ?? "none";
  const show = action === "interact" || action === "emote" || action === "verb";
  const extra = panelEl.querySelector("#player-turn-action-extra");
  if (extra) {
    extra.classList.toggle("hidden", !show);
  }

  const verbInput = panelEl.querySelector("#player-turn-verb");
  const verbSelect = panelEl.querySelector("#player-turn-verb-select");
  const verbLabel = panelEl.querySelector("#player-turn-verb-label");
  const targetLabel = panelEl.querySelector("#player-turn-target-label");

  const isVerbAction = action === "verb";
  verbInput?.classList.toggle("hidden", isVerbAction);
  if (verbInput) {
    verbInput.toggleAttribute("disabled", isVerbAction);
    verbInput.setAttribute("aria-hidden", isVerbAction ? "true" : "false");
  }
  verbSelect?.classList.toggle("hidden", !isVerbAction);
  if (verbSelect) {
    verbSelect.toggleAttribute("disabled", !isVerbAction);
    verbSelect.setAttribute("aria-hidden", isVerbAction ? "false" : "true");
  }

  if (verbLabel) {
    verbLabel.textContent = isVerbAction ? "Turn verb" : "Verb";
  }
  if (targetLabel) {
    targetLabel.textContent = isVerbAction ? "Target (item id, optional)" : "Target";
  }

  if (isVerbAction) {
    populateTurnVerbSelect(panelEl);
    prefillAssistVerbTurn(panelEl);
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

async function loadTurnVerbCatalog() {
  try {
    const data = await fetchTurnVerbs();
    turnVerbCatalog = data.verbs || [];
  } catch {
    turnVerbCatalog = [];
  }
}

async function loadPlayerTurnAssist() {
  try {
    const data = await fetchPlayerTurnAssist();
    assistTargets = Array.isArray(data.targets) ? data.targets : [];
  } catch {
    assistTargets = [];
  }
}

export async function loadPlayerTurnVerbCatalog() {
  await loadTurnVerbCatalog();
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

  void Promise.all([loadTurnVerbCatalog(), loadPlayerTurnAssist()]).then(() => {
    syncActionFieldVisibility(panelEl);
  });

  const actionSelect = panelEl.querySelector('[name="action"]');
  actionSelect?.addEventListener("change", () => {
    syncActionFieldVisibility(panelEl);
  });

  const targetInput = panelEl.querySelector('[name="target"]');
  targetInput?.addEventListener("input", () => {
    const action = panelEl.querySelector('[name="action"]')?.value ?? "none";
    if (action === "verb") {
      populateTurnVerbSelect(panelEl);
      prefillAssistVerbTurn(panelEl);
    }
  });

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

export async function syncPlayerTurnPanel(snapshot) {
  if (!panelEl) return;
  const snap = normalizeSnapshot(snapshot ?? getSnapshot());
  await Promise.all([loadTurnVerbCatalog(), loadPlayerTurnAssist()]);

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
