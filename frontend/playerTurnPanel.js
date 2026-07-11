/**
 * Inline player turn form (1.1.0) and shared field defs for manual compound turns.
 */

import { buildCompoundTurnPayload, fetchTurnVerbs } from "./api.js";
import { asArray, normalizeSnapshot } from "./snapshot.js";

/** @type {{ id: string, description?: string }[]} */
let turnVerbCatalog = [];

const INVENTORY_PICK_UP_HANDLER = "inventory_pick_up";

function isInventoryOnlyHandler(handlerId) {
  if (!handlerId || handlerId === INVENTORY_PICK_UP_HANDLER) return false;
  return String(handlerId).startsWith("inventory_");
}

function inventoryVerbsForItem(item) {
  const verbs = ["drop"];
  const actions = item?.actions || {};
  for (const [name, payload] of Object.entries(actions).sort()) {
    if (name === "pick_up" || !payload || typeof payload !== "object") continue;
    if (payload.kind && payload.kind !== "interact") continue;
    if (isInventoryOnlyHandler(payload.handler_id)) {
      verbs.push(name);
    }
  }
  return verbs;
}

function carriedItemsForAgent(snapshot) {
  const snap = normalizeSnapshot(snapshot);
  const agentId = snap?.active_agent_id;
  const byAgent = snap?.extensions?.inventory?.by_agent;
  if (!agentId || !byAgent || !Array.isArray(byAgent[agentId])) return [];
  return byAgent[agentId];
}

function carriedItemById(snapshot, itemId) {
  const cleaned = String(itemId || "").trim();
  if (!cleaned) return null;
  return carriedItemsForAgent(snapshot).find((item) => item?.item_id === cleaned) || null;
}

function verbsForTurnDropdown(snapshot, targetItemId) {
  const item = carriedItemById(snapshot, targetItemId);
  if (!item) return turnVerbCatalog;
  const allowed = new Set(inventoryVerbsForItem(item));
  return turnVerbCatalog.filter((verb) => allowed.has(verb.id));
}

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
        { value: "verb", label: "verb" },
      ],
    },
    {
      name: "target",
      label: "Target (interact / emote / verb)",
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
    (action === "interact" || action === "emote")
    && (!String(data.target ?? "").trim() || !String(data.verb ?? "").trim())
  ) {
    return "Interact and emote turns require target and verb.";
  }
  if (action === "verb" && !String(data.verb ?? "").trim()) {
    return "Verb turns require a registered turn verb.";
  }
  if (!String(data.reasoning ?? "").trim()) {
    return "Reasoning is required.";
  }
  return null;
}

function populateTurnVerbSelect(panelEl, snapshot) {
  const select = panelEl.querySelector("#player-turn-verb-select");
  if (!select) return;
  const previous = select.value;
  const targetId = panelEl.querySelector('[name="target"]')?.value ?? "";
  const verbs = verbsForTurnDropdown(snapshot, targetId);
  select.innerHTML = "";
  const blank = document.createElement("option");
  blank.value = "";
  blank.textContent = "(select turn verb)";
  select.appendChild(blank);
  for (const verb of verbs) {
    const option = document.createElement("option");
    option.value = verb.id;
    option.textContent = verb.description
      ? `${verb.id} — ${verb.description}`
      : verb.id;
    select.appendChild(option);
  }
  if (previous && [...select.options].some((opt) => opt.value === previous)) {
    select.value = previous;
  } else if (verbs.length === 1) {
    select.value = verbs[0].id;
  }
}

function prefillInventoryVerbTurn(panelEl, snapshot) {
  const action = panelEl.querySelector('[name="action"]')?.value ?? "none";
  if (action !== "verb") return;

  const targetInput = panelEl.querySelector('[name="target"]');
  const carried = carriedItemsForAgent(snapshot);
  if (targetInput && !String(targetInput.value || "").trim() && carried.length === 1) {
    targetInput.value = carried[0].item_id || "";
  }

  const targetId = targetInput?.value ?? "";
  const item = carriedItemById(snapshot, targetId);
  if (!item) return;

  const verbs = inventoryVerbsForItem(item).filter((name) => name !== "drop");
  const select = panelEl.querySelector("#player-turn-verb-select");
  if (!select || select.value || verbs.length !== 1) return;
  if ([...select.options].some((opt) => opt.value === verbs[0])) {
    select.value = verbs[0];
  }
}

function syncActionFieldVisibility(panelEl, snapshot) {
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
    targetLabel.textContent = isVerbAction
      ? "Target (item id, optional)"
      : "Target";
  }

  if (isVerbAction) {
    populateTurnVerbSelect(panelEl, snapshot);
    prefillInventoryVerbTurn(panelEl, snapshot);
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
let lastSyncedSnapshot = null;

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

  void loadTurnVerbCatalog().then(() => {
    const snapshot = getSnapshot();
    populateTurnVerbSelect(panelEl, snapshot);
    syncActionFieldVisibility(panelEl, snapshot);
  });

  const actionSelect = panelEl.querySelector('[name="action"]');
  actionSelect?.addEventListener("change", () => {
    syncActionFieldVisibility(panelEl, getSnapshot());
  });

  const targetInput = panelEl.querySelector('[name="target"]');
  targetInput?.addEventListener("input", () => {
    const action = panelEl.querySelector('[name="action"]')?.value ?? "none";
    if (action === "verb") {
      populateTurnVerbSelect(panelEl, getSnapshot());
      prefillInventoryVerbTurn(panelEl, getSnapshot());
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
  const inventoryChanged =
    JSON.stringify(snap?.extensions?.inventory) !==
    JSON.stringify(lastSyncedSnapshot?.extensions?.inventory);
  if (inventoryChanged || !turnVerbCatalog.length) {
    await loadTurnVerbCatalog();
  }
  lastSyncedSnapshot = snap;

  populateTurnVerbSelect(panelEl, snap);
  const active = asArray(snap?.agents).find((agent) => agent.id === snap?.active_agent_id);
  const coordinateMode = getCoordinateMode();

  updateMoveHints(panelEl, coordinateMode);
  syncActionFieldVisibility(panelEl, snap);

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
