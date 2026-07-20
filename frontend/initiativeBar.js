/** Initiative bar + configure modal (Studio 1.7.1). */

import {
  postInitiativeNext,
  postInitiativeOrder,
  putInitiative,
} from "./api.js";
import { asArray, normalizeSnapshot } from "./snapshot.js";
import { showToast } from "./ui.js";

const barEl = document.getElementById("initiative-bar");
const summaryEl = document.getElementById("initiative-summary");
const trackEl = document.getElementById("initiative-track");
const configBtn = document.getElementById("initiative-config");
const nextBtn = document.getElementById("initiative-next");
const modalBackdrop = document.getElementById("initiative-modal-backdrop");
const modalList = document.getElementById("initiative-order-list");
const modalEnable = document.getElementById("initiative-modal-enable");
const modalError = document.getElementById("initiative-modal-error");
const modalCancel = document.getElementById("initiative-modal-cancel");
const modalSave = document.getElementById("initiative-modal-save");

/** @type {((snapshot: object) => void) | null} */
let onSnapshot = null;

/** @type {string[]} */
let draftOrder = [];

function closeModal() {
  modalBackdrop?.classList.add("hidden");
  if (modalError) modalError.textContent = "";
}

function agentById(snapshot, agentId) {
  return asArray(snapshot?.agents).find((a) => a.id === agentId) ?? null;
}

function renderTrack(snapshot) {
  if (!trackEl) return;
  const init = snapshot?.initiative;
  trackEl.innerHTML = "";
  if (!init?.enabled) {
    trackEl.classList.add("hidden");
    return;
  }
  trackEl.classList.remove("hidden");
  const entries = asArray(init.entries);
  const maxVisible = 8;
  for (const entry of entries.slice(0, maxVisible)) {
    const pill = document.createElement("span");
    pill.className = `initiative-pill${entry.is_current ? " initiative-pill--current" : ""}`;
    pill.textContent = entry.agent_name || entry.agent_id;
    pill.title = entry.agent_id;
    trackEl.appendChild(pill);
  }
  if (entries.length > maxVisible) {
    const more = document.createElement("span");
    more.className = "initiative-pill initiative-pill--more";
    more.textContent = `+${entries.length - maxVisible}`;
    trackEl.appendChild(more);
  }
}

export function renderInitiativeBar(snapshot) {
  const snap = normalizeSnapshot(snapshot);
  const init = snap.initiative || { enabled: false };
  if (!barEl) return;

  barEl.classList.toggle("initiative-bar--on", Boolean(init.enabled));
  if (summaryEl) {
    if (init.enabled) {
      const current = asArray(init.entries).find((e) => e.is_current);
      const name = current?.agent_name || init.current_agent_id || "—";
      summaryEl.textContent = `Initiative · Round ${init.round ?? 1} · Now: ${name}`;
    } else {
      summaryEl.textContent = "Initiative off";
    }
  }
  renderTrack(snap);
  nextBtn?.classList.toggle("hidden", !init.enabled);
  if (configBtn) {
    configBtn.textContent = init.enabled ? "Edit order…" : "Configure…";
  }
}

function buildDraftFromSnapshot(snapshot) {
  const init = snapshot?.initiative;
  if (init?.enabled && asArray(init.order).length) {
    return [...init.order];
  }
  return asArray(snapshot?.agents).map((a) => a.id);
}

/** @type {object | null} */
let lastModalSnapshot = null;

function renderModalList() {
  const snapshot = lastModalSnapshot;
  if (!modalList || !snapshot) return;
  modalList.innerHTML = "";
  const agents = asArray(snapshot?.agents);

  const inOrder = new Set(draftOrder);

  for (const agentId of draftOrder) {
    const agent = agentById(snapshot, agentId);
    if (!agent) continue;
    modalList.appendChild(createOrderRow(agent, true));
  }

  const addWrap = document.createElement("div");
  addWrap.className = "initiative-add-row";
  const label = document.createElement("label");
  label.textContent = "Add agent";
  const select = document.createElement("select");
  select.className = "session-meta-input";
  const empty = document.createElement("option");
  empty.value = "";
    empty.textContent = "(select agent)";
  select.appendChild(empty);
  for (const agent of agents) {
    if (inOrder.has(agent.id)) continue;
    const opt = document.createElement("option");
    opt.value = agent.id;
    opt.textContent = `${agent.name} (${agent.id})`;
    select.appendChild(opt);
  }
  select.addEventListener("change", () => {
    if (!select.value || draftOrder.includes(select.value)) return;
    draftOrder.push(select.value);
    renderModalList();
  });
  label.appendChild(select);
  addWrap.appendChild(label);
  modalList.appendChild(addWrap);
}

function createOrderRow(agent, inOrder) {
  const row = document.createElement("div");
  row.className = "initiative-order-row";
  row.dataset.agentId = agent.id;

  const up = document.createElement("button");
  up.type = "button";
  up.className = "initiative-order-move";
  up.textContent = "↑";
  up.title = "Move up";
  up.addEventListener("click", () => moveAgent(agent.id, -1));

  const down = document.createElement("button");
  down.type = "button";
  down.className = "initiative-order-move";
  down.textContent = "↓";
  down.title = "Move down";
  down.addEventListener("click", () => moveAgent(agent.id, 1));

  const name = document.createElement("span");
  name.className = "initiative-order-name";
  name.textContent = `${agent.name}${agent.is_player ? " (player)" : ""}`;

  const remove = document.createElement("button");
  remove.type = "button";
  remove.className = "initiative-order-remove";
  remove.textContent = "Remove";
  remove.addEventListener("click", () => {
    draftOrder = draftOrder.filter((id) => id !== agent.id);
    renderModalList();
  });

  row.appendChild(up);
  row.appendChild(down);
  row.appendChild(name);
  if (inOrder) row.appendChild(remove);
  return row;
}

function moveAgent(agentId, delta) {
  const idx = draftOrder.indexOf(agentId);
  if (idx < 0) return;
  const next = idx + delta;
  if (next < 0 || next >= draftOrder.length) return;
  const copy = [...draftOrder];
  const [item] = copy.splice(idx, 1);
  copy.splice(next, 0, item);
  draftOrder = copy;
  renderModalList();
}

function openModal(snapshot) {
  if (!modalBackdrop) return;
  lastModalSnapshot = normalizeSnapshot(snapshot);
  draftOrder = buildDraftFromSnapshot(lastModalSnapshot);
  if (modalEnable) {
    modalEnable.checked = Boolean(lastModalSnapshot?.initiative?.enabled);
  }
  if (modalError) modalError.textContent = "";
  renderModalList();
  modalBackdrop.classList.remove("hidden");
}

async function saveModal() {
  if (!modalEnable || !modalSave) return;
  const enabled = modalEnable.checked;
  if (modalError) modalError.textContent = "";
  modalSave.disabled = true;
  try {
    if (enabled && !draftOrder.length) {
      throw new Error("Add at least one agent to the initiative order.");
    }
    const orderResult = await postInitiativeOrder(draftOrder);
    if (!orderResult.ok) {
      throw new Error(orderResult.message || "Failed to save order.");
    }
    const putResult = await putInitiative({ enabled });
    if (!putResult.ok) {
      throw new Error(putResult.message || "Failed to update initiative.");
    }
    if (putResult.snapshot && onSnapshot) {
      onSnapshot(putResult.snapshot);
    }
    closeModal();
    showToast(enabled ? "Initiative enabled." : "Initiative disabled.");
  } catch (err) {
    if (modalError) modalError.textContent = String(err.message || err);
  } finally {
    modalSave.disabled = false;
  }
}

async function advanceNext() {
  if (!nextBtn) return;
  nextBtn.disabled = true;
  try {
    const result = await postInitiativeNext();
    if (!result.ok) {
      throw new Error(result.message || "Failed to advance initiative.");
    }
    if (result.snapshot && onSnapshot) {
      onSnapshot(result.snapshot);
    }
  } catch (err) {
    showToast(String(err.message || err), true);
  } finally {
    nextBtn.disabled = false;
  }
}

export function initInitiativeBar({ onSnapshotUpdate } = {}) {
  onSnapshot = onSnapshotUpdate ?? null;
  configBtn?.addEventListener("click", () => {
    if (lastModalSnapshot) openModal(lastModalSnapshot);
  });
  nextBtn?.addEventListener("click", () => void advanceNext());
  modalCancel?.addEventListener("click", closeModal);
  modalBackdrop?.addEventListener("click", (e) => {
    if (e.target === modalBackdrop) closeModal();
  });
  modalSave?.addEventListener("click", () => {
    void saveModal();
  });
}

export function syncInitiativeSnapshot(snapshot) {
  lastModalSnapshot = normalizeSnapshot(snapshot);
}

export function initiativeBlocksRunTurn(snapshot) {
  const init = snapshot?.initiative;
  if (!init?.enabled) return { blocked: false };
  const currentId = init.current_agent_id;
  const agent = asArray(snapshot?.agents).find((a) => a.id === currentId);
  if (!agent) return { blocked: true, reason: "Initiative: no current actor." };
  if (agent.is_player) {
    return {
      blocked: true,
      reason: `Initiative: waiting for ${agent.name} (player).`,
    };
  }
  return { blocked: false, currentAgent: agent };
}
