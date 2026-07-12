/**
 * campaign-rpg-studio frontend — grid, edit menus, LLM turn, sidebar (V0.3.1b–0.4.0c2).
 */

import { hasAppearance, resolveAppearanceUrl } from "./appearance.js";
import {
  exportSession,
  getHealth,
  getPrompt,
  getState,
  importSession,
  postManualTurn,
  postTurn,
} from "./api.js";
import { initPromptLayout, reloadPromptLayoutIfOpen } from "./promptLayout.js";
import { initAppTabs } from "./tabs.js";
import { initLorebooks, refreshLorebookList, refreshLorebookScanPanel } from "./lorebooks.js";
import { initTemplates } from "./templates.js";
import { initPlugins } from "./plugins.js";
import { clearHandlerChoicesCache } from "./objectActions.js";
import {
  buildPlayerTurnPayloadFromPanel,
  initPlayerTurnPanel,
  loadPlayerTurnVerbCatalog,
  setPlayerTurnPanelBusy,
  syncPlayerTurnPanel,
} from "./playerTurnPanel.js";
import { initVisionUnits, syncVisionUnitsFromSnapshot } from "./visionUnits.js";
import { initCoordinateMode, syncCoordinateModeFromSnapshot } from "./coordinateMode.js";
import { initDecorations, renderSceneDecorations } from "./decorations.js";
import { initGridViewport, maybeCenterGrid, CELL_SIZE } from "./gridViewport.js";
import {
  appendTurnLogEntry,
  bindPromptDebug,
  bindResponseDebug,
  clearTurnLog,
  renderAgentsElsewhere,
  renderLastPrompt,
  renderLastResponse,
  renderPassiveVision,
  renderRecentEvents,
  renderTurnLog,
  setLastPrompt,
  setLastResponse,
} from "./panels.js";
import { activeAreaView, asArray, isMultiTileObject, normalizeSnapshot, objectFootprintSize } from "./snapshot.js";
import {
  bindActiveAgentSelect,
  bindActiveAreaSelect,
  bindAreaManageButtons,
  bindEmitEventButton,
  bindGridContextMenu,
  initUi,
  openPlayerTurnModal,
  renderActiveAgentSelect,
  renderActiveAreaSelect,
  showToast,
} from "./ui.js";
import { initSettings } from "./settings.js";

const subtitleEl = document.getElementById("app-subtitle");
const statusEl = document.getElementById("status");
const gridViewportEl = document.getElementById("grid-viewport");
const gridWorldEl = document.getElementById("grid-world");
const gridEl = document.getElementById("grid");
const gridViewportBackgroundEl = document.getElementById("grid-viewport-background");
const gridSpritesEl = document.getElementById("grid-sprites");
const gridLinesEl = document.getElementById("grid-lines");
const gridOverlayEl = document.getElementById("grid-overlay");
const snapshotEl = document.getElementById("snapshot");
const sessionMetaEl = document.getElementById("session-meta");
const visionUnitsInput = document.getElementById("vision-units-input");
const visionUnitsPerTileInput = document.getElementById("vision-units-per-tile-input");
const coordinateModeSelect = document.getElementById("coordinate-mode-select");
const passiveVisionEl = document.getElementById("passive-vision");
const passiveVisionEmptyEl = document.getElementById("passive-vision-empty");
const agentsElsewhereEl = document.getElementById("agents-elsewhere");
const agentsElsewhereEmptyEl = document.getElementById("agents-elsewhere-empty");
const recentEventsEl = document.getElementById("recent-events");
const recentEventsEmptyEl = document.getElementById("recent-events-empty");
const turnLogEl = document.getElementById("turn-log");
const turnLogEmptyEl = document.getElementById("turn-log-empty");
const lastPromptEl = document.getElementById("last-prompt");
const lastPromptEmptyEl = document.getElementById("last-prompt-empty");
const lastResponseEl = document.getElementById("last-response");
const lastResponseEmptyEl = document.getElementById("last-response-empty");
const lastResponseTokensEl = document.getElementById("last-response-tokens");
const promptLayoutEl = document.getElementById("prompt-layout");
const promptLayoutStatusEl = document.getElementById("prompt-layout-status");
const promptBlockListEl = document.getElementById("prompt-block-list");
const promptLayoutSaveBtn = document.getElementById("prompt-layout-save");
const promptLayoutResetBtn = document.getElementById("prompt-layout-reset");
const promptLayoutPreviewBtn = document.getElementById("prompt-layout-preview");
const promptLayoutPreviewEl = document.getElementById("prompt-layout-preview");
const promptLayoutPreviewEmptyEl = document.getElementById("prompt-layout-preview-empty");
const promptAddTypeSelect = document.getElementById("prompt-add-type");
const promptAddVariantWrap = document.getElementById("prompt-add-variant-wrap");
const promptAddVariantLabel = document.getElementById("prompt-add-variant-label");
const promptAddVariantSelect = document.getElementById("prompt-add-variant");
const promptAddContentWrap = document.getElementById("prompt-add-content-wrap");
const promptAddContentInput = document.getElementById("prompt-add-content");
const promptAddBtn = document.getElementById("prompt-add-btn");
const promptDebugEl = document.getElementById("prompt-debug");
const responseDebugEl = document.getElementById("response-debug");
const activeAreaSelect = document.getElementById("active-area-select");
const createAreaBtn = document.getElementById("create-area");
const editAreaBtn = document.getElementById("edit-area");
const saveAreaTemplateBtn = document.getElementById("save-area-template");
const loadAreaTemplateBtn = document.getElementById("load-area-template");
const deleteAreaBtn = document.getElementById("delete-area");
const activeAgentSelect = document.getElementById("active-agent-select");
const runTurnBtn = document.getElementById("run-turn");
const runTurnHintEl = document.getElementById("run-turn-hint");
const playerTurnPanelEl = document.getElementById("player-turn-panel");
const playerTurnHeadingEl = document.getElementById("player-turn-heading");
const playerTurnSubmitBtn = document.getElementById("player-turn-submit");
const emitEventBtn = document.getElementById("emit-event");
const sessionExportBtn = document.getElementById("session-export");
const sessionImportBtn = document.getElementById("session-import");
const sessionImportInput = document.getElementById("session-import-input");

let lastSnapshot = null;
let turnInFlight = false;
let promptTokenHintSeq = 0;

function resolveActiveAgentIdForPrompt() {
  return lastSnapshot?.active_agent_id ?? activeAgentSelect?.value ?? undefined;
}

function setRunTurnTokenHint(text) {
  const hint = String(text ?? "").trim();
  if (runTurnHintEl) {
    runTurnHintEl.textContent = hint;
  }
}

function activeAgentFromSnapshot(snapshot) {
  const snap = normalizeSnapshot(snapshot ?? lastSnapshot);
  return asArray(snap.agents).find((agent) => agent.id === snap.active_agent_id) ?? null;
}

function getCoordinateMode() {
  return lastSnapshot?.coordinate_mode === "relative" ? "relative" : "full";
}

function findAgentById(agentId) {
  const snap = normalizeSnapshot(lastSnapshot);
  return asArray(snap.agents).find((agent) => agent.id === agentId) ?? null;
}

function setTurnBusy(busy) {
  turnInFlight = busy;
  if (runTurnBtn) runTurnBtn.disabled = busy;
  setPlayerTurnPanelBusy(busy);
}

async function refreshRunTurnTokenHint() {
  if (turnInFlight || !runTurnBtn) return;
  const active = activeAgentFromSnapshot();
  if (active?.is_player) {
    setRunTurnTokenHint("Player agent — use the turn form below (no LLM)");
    return;
  }
  const seq = ++promptTokenHintSeq;
  const agentId = resolveActiveAgentIdForPrompt();
  try {
    const data = await getPrompt(agentId);
    if (seq !== promptTokenHintSeq) return;
    if (data.prompt_tokens != null) {
      setRunTurnTokenHint(
        `~${Number(data.prompt_tokens).toLocaleString()} input tokens (estimate)`,
      );
    }
  } catch {
    // keep previous hint if any
  }
}

function posKey(x, y) {
  return `${x},${y}`;
}

function buildFootprintCoverKeys(objects) {
  const covered = new Set();
  for (const object of asArray(objects)) {
    if (!isMultiTileObject(object)) continue;
    const { width, height } = objectFootprintSize(object);
    const [ax, ay] = object.position;
    for (let dx = 0; dx < width; dx++) {
      for (let dy = 0; dy < height; dy++) {
        if (dx !== 0 || dy !== 0) {
          covered.add(posKey(ax + dx, ay + dy));
        }
      }
    }
  }
  return covered;
}

function entityFootprintSize(entity, kind) {
  if (kind === "agent") {
    return { width: 1, height: 1 };
  }
  return objectFootprintSize(entity);
}

function createFootprintMarker(entity, kind, grid, isActive = false) {
  const marker = document.createElement("div");
  const hiddenObject = kind === "object" && entity.hidden;
  marker.className = `footprint-marker footprint-marker-${kind}${isActive ? " footprint-marker-active" : ""}${hiddenObject ? " footprint-marker-hidden" : ""}`;
  marker.dataset.kind = kind;
  marker.dataset.id = entity.id;
  marker.title = `${entity.name} (${entity.id})${hiddenObject ? " — hidden" : ""}`;

  const { width, height } = entityFootprintSize(entity, kind);
  const [ax, ay] = entity.position;
  marker.style.left = `${(ax - grid.min_x) * CELL_SIZE}px`;
  marker.style.top = `${(ay - grid.min_y) * CELL_SIZE}px`;
  marker.style.width = `${width * CELL_SIZE}px`;
  marker.style.height = `${height * CELL_SIZE}px`;

  const inner = createEntityMarker(entity, kind, isActive);
  inner.classList.add("footprint-marker-inner");
  marker.appendChild(inner);
  return marker;
}

function createNameChip(entity, kind, isActive) {
  const chip = document.createElement("div");
  chip.className = `chip chip-${kind}${isActive ? " chip-active" : ""}`;
  chip.dataset.kind = kind;
  chip.dataset.id = entity.id;
  chip.title = `${entity.name} (${entity.id})`;
  chip.textContent = entity.name;
  if (isActive) {
    const star = document.createElement("span");
    star.className = "chip-active-mark";
    star.textContent = " ★";
    star.setAttribute("aria-label", "active agent");
    chip.appendChild(star);
  }
  return chip;
}

function createTokenMarker(entity, kind, isActive) {
  const token = document.createElement("div");
  token.className = `token token-${kind}${isActive ? " token-active" : ""}`;
  token.dataset.kind = kind;
  token.dataset.id = entity.id;
  token.title = `${entity.name} (${entity.id})`;

  const img = document.createElement("img");
  img.className = "token-img";
  img.src = resolveAppearanceUrl(entity.appearance);
  img.alt = entity.name;
  img.draggable = false;
  img.addEventListener("error", () => {
    token.replaceWith(createNameChip(entity, kind, isActive));
  });
  token.appendChild(img);

  if (isActive) {
    const star = document.createElement("span");
    star.className = "token-active-mark";
    star.textContent = "★";
    star.setAttribute("aria-label", "active agent");
    token.appendChild(star);
  }
  return token;
}

function createEntityMarker(entity, kind, isActive) {
  if (hasAppearance(entity)) {
    return createTokenMarker(entity, kind, isActive);
  }
  return createNameChip(entity, kind, isActive);
}

function renderGrid(data) {
  const view = activeAreaView(data);
  const { grid, active_agent_id } = view;
  if (!grid) {
    gridEl.innerHTML = "";
    if (gridOverlayEl) gridOverlayEl.innerHTML = "";
    if (gridViewportBackgroundEl) gridViewportBackgroundEl.innerHTML = "";
    if (gridSpritesEl) gridSpritesEl.innerHTML = "";
    if (gridLinesEl) gridLinesEl.innerHTML = "";
    gridEl.classList.add("grid-empty");
    return;
  }
  gridEl.classList.remove("grid-empty");
  const objects = asArray(view.objects);
  const agents = asArray(view.agents);
  const footprintCover = buildFootprintCoverKeys(objects);

  const width = grid.max_x - grid.min_x + 1;
  const height = grid.max_y - grid.min_y + 1;

  gridEl.style.setProperty("--grid-cols", String(width));
  gridEl.style.setProperty("--grid-rows", String(height));
  const pixelWidth = width * CELL_SIZE;
  const pixelHeight = height * CELL_SIZE;
  gridEl.style.width = `${pixelWidth}px`;
  gridEl.style.height = `${pixelHeight}px`;
  gridEl.innerHTML = "";
  if (gridOverlayEl) {
    gridOverlayEl.innerHTML = "";
    gridOverlayEl.style.width = `${pixelWidth}px`;
    gridOverlayEl.style.height = `${pixelHeight}px`;
  }

  for (let y = grid.min_y; y <= grid.max_y; y++) {
    for (let x = grid.min_x; x <= grid.max_x; x++) {
      const tile = document.createElement("div");
      tile.className = "tile";
      if (footprintCover.has(posKey(x, y))) {
        tile.classList.add("tile-covered");
      }
      tile.dataset.x = String(x);
      tile.dataset.y = String(y);

      const coord = document.createElement("span");
      coord.className = "tile-coord";
      coord.textContent = `${x}, ${y}`;
      tile.appendChild(coord);

      gridEl.appendChild(tile);
    }
  }

  if (gridOverlayEl) {
    for (const object of objects) {
      gridOverlayEl.appendChild(createFootprintMarker(object, "object", grid));
    }
    for (const agent of agents) {
      gridOverlayEl.appendChild(
        createFootprintMarker(agent, "agent", grid, agent.id === active_agent_id),
      );
    }
  }

  renderSceneDecorations(view, {
    gridViewportBackgroundEl,
    gridSpritesEl,
    gridLinesEl,
    gridEl,
  });

  maybeCenterGrid(gridEl);
}

function renderSessionMeta(data) {
  const snap = normalizeSnapshot(data);
  const view = activeAreaView(snap);
  const agents = asArray(view.agents);
  const objects = asArray(view.objects);
  const allAgents = asArray(snap.agents);
  const active = allAgents.find((a) => a.id === snap.active_agent_id);
  const activeLabel = active ? `${active.name} (${active.id})` : snap.active_agent_id;
  const areaDesc = snap.areas?.[snap.active_area_id]?.area_description ?? "";

  sessionMetaEl.innerHTML = `
    <dt>Session turn</dt><dd>${snap.session_turn ?? "?"}</dd>
    <dt>Active area</dt><dd>${escapeHtml(snap.active_area_id ?? "—")}</dd>
    <dt>Area description</dt><dd>${escapeHtml(areaDesc)}</dd>
    <dt>Active agent</dt><dd>${escapeHtml(activeLabel ?? "—")}</dd>
    <dt>Agents (this area)</dt><dd>${agents.length}</dd>
    <dt>Objects (this area)</dt><dd>${objects.length}</dd>
  `;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function renderSidebarPanels(data) {
  renderPassiveVision(data, passiveVisionEl, passiveVisionEmptyEl);
  renderAgentsElsewhere(data, agentsElsewhereEl, agentsElsewhereEmptyEl);
  renderRecentEvents(activeAreaView(data), recentEventsEl, recentEventsEmptyEl);
}

function renderState(data) {
  lastSnapshot = normalizeSnapshot(data);
  renderGrid(lastSnapshot);
  renderSessionMeta(lastSnapshot);
  syncVisionUnitsFromSnapshot(lastSnapshot);
  syncCoordinateModeFromSnapshot(lastSnapshot);
  renderSidebarPanels(lastSnapshot);
  if (activeAreaSelect) renderActiveAreaSelect(activeAreaSelect, lastSnapshot);
  if (activeAgentSelect) renderActiveAgentSelect(activeAgentSelect, lastSnapshot);
  snapshotEl.textContent = JSON.stringify(lastSnapshot, null, 2);
  syncPlayerTurnPanel(lastSnapshot);
  void refreshRunTurnTokenHint();
}

async function fetchState() {
  statusEl.textContent = "Fetching…";
  try {
    const data = await getState();
    renderState(data);
    updateStatusLine(lastSnapshot);
  } catch (err) {
    gridEl.innerHTML = "";
    if (gridOverlayEl) gridOverlayEl.innerHTML = "";
    gridEl.classList.add("grid-empty");
    snapshotEl.textContent = String(err.message || err);
    statusEl.textContent = `Error — ${err.message || err}`;
    showToast(String(err.message || err), true);
  }
}

function updateStatusLine(data) {
  const snap = normalizeSnapshot(data);
  const active = asArray(snap.agents).find((a) => a.id === snap.active_agent_id);
  const area = snap.active_area_id ?? "area";
  const agentName = active ? active.name : snap.active_agent_id ?? "—";
  statusEl.textContent = `Turn ${snap.session_turn ?? "?"} — ${area} — ${agentName}`;
}

function recordTurnResult(result, { agentId, agentName } = {}) {
  const snap = normalizeSnapshot(result.snapshot || lastSnapshot);
  const agent = agentId
    ? asArray(snap.agents).find((item) => item.id === agentId)
    : asArray(snap.agents).find((item) => item.id === snap.active_agent_id);
  appendTurnLogEntry({
    sessionTurn: snap.session_turn ?? "?",
    agentName: agentName ?? agent?.name ?? "Agent",
    message: result.message,
    steps: result.steps,
  });
  renderTurnLog(turnLogEl, turnLogEmptyEl);
  if (result.prompt) {
    setLastPrompt(result.prompt);
    if (promptDebugEl.open) {
      renderLastPrompt(lastPromptEl, lastPromptEmptyEl);
    }
  }
  if (result.llm_response) {
    setLastResponse(result.llm_response, {
      prompt: result.prompt_tokens ?? null,
      completion: result.completion_tokens ?? null,
      total: result.total_tokens ?? null,
      estimate: result.prompt_tokens_estimate ?? null,
    });
    if (responseDebugEl.open) {
      renderLastResponse(lastResponseEl, lastResponseEmptyEl, lastResponseTokensEl);
    }
  }
}

async function executeTurnResult(result, turnMeta = {}) {
  if (!result.ok) {
    showToast(result.message, true);
    statusEl.textContent = "Turn failed";
    return;
  }
  if (result.snapshot) {
    renderState(result.snapshot);
    updateStatusLine(result.snapshot);
  } else {
    await fetchState();
  }
  recordTurnResult(result, turnMeta);
  const stepCount = Array.isArray(result.steps) ? result.steps.length : 0;
  const suffix = stepCount ? ` (${stepCount} step${stepCount === 1 ? "" : "s"})` : "";
  showToast(`${result.message}${suffix}`, false);
}

async function runManualTurnForAgent(agentId, compoundTurn, turnMeta = {}) {
  if (turnInFlight) return;
  const agent = findAgentById(agentId);
  const label = turnMeta.agentName ?? agent?.name ?? agentId;
  setTurnBusy(true);
  statusEl.textContent = `Running player turn (${label})…`;
  try {
    const result = await postManualTurn({ agentId, compoundTurn });
    await executeTurnResult(result, { agentId, agentName: label });
  } catch (err) {
    showToast(String(err.message || err), true);
    statusEl.textContent = "Error";
  } finally {
    setTurnBusy(false);
  }
}

async function runLlmTurnForAgent(agentId, turnMeta = {}) {
  if (turnInFlight) return;
  const agent = findAgentById(agentId);
  if (agent?.is_player) {
    showToast(`${agent.name} is a player agent — use the manual turn form.`, true);
    return;
  }
  const label = turnMeta.agentName ?? agent?.name ?? agentId ?? "active agent";
  setTurnBusy(true);
  statusEl.textContent = `Running LLM turn (${label})…`;
  try {
    const result = await postTurn({ agentId });
    await executeTurnResult(result, { agentId, agentName: label });
  } catch (err) {
    showToast(String(err.message || err), true);
    statusEl.textContent = "Error";
  } finally {
    setTurnBusy(false);
  }
}

async function runAgentTurn(agentId, compoundTurn = null) {
  const agent = findAgentById(agentId);
  if (!agent) {
    showToast(`Agent ${agentId} not found.`, true);
    return;
  }
  if (compoundTurn) {
    await runManualTurnForAgent(agentId, compoundTurn, { agentName: agent.name });
    return;
  }
  if (agent.is_player) {
    openPlayerTurnModal(
      agent.name,
      (payload) => runManualTurnForAgent(agentId, payload, { agentName: agent.name }),
      getCoordinateMode(),
    );
    return;
  }
  await runLlmTurnForAgent(agentId, { agentName: agent.name });
}

async function runTurn() {
  if (turnInFlight) return;
  const active = activeAgentFromSnapshot();
  if (!active) {
    showToast("No active agent.", true);
    return;
  }
  if (active.is_player) {
    try {
      const compoundTurn = buildPlayerTurnPayloadFromPanel();
      await runManualTurnForAgent(active.id, compoundTurn, { agentName: active.name });
    } catch (err) {
      showToast(String(err.message || err), true);
    }
    return;
  }
  await runLlmTurnForAgent(active.id, { agentName: active.name });
}

async function refreshAfterMutation(snapshot) {
  if (snapshot) {
    renderState(snapshot);
    updateStatusLine(lastSnapshot);
    await reloadPromptLayoutIfOpen();
    void refreshLorebookScanPanel();
    return;
  }
  await fetchState();
  await reloadPromptLayoutIfOpen();
  void refreshLorebookScanPanel();
}

initUi({
  getSnapshotFn: () => activeAreaView(lastSnapshot),
  onStateChangedFn: refreshAfterMutation,
  onRunAgentTurnFn: runAgentTurn,
  getCoordinateModeFn: getCoordinateMode,
});
initPlayerTurnPanel({
  panelFormEl: playerTurnPanelEl,
  headingEl: playerTurnHeadingEl,
  submitBtnEl: playerTurnSubmitBtn,
  getSnapshotFn: () => lastSnapshot,
  getCoordinateModeFn: getCoordinateMode,
  showToastFn: showToast,
  onSubmitFn: async (compoundTurn) => {
    const active = activeAgentFromSnapshot();
    if (!active?.is_player) {
      showToast("Active agent is not a player.", true);
      return;
    }
    await runManualTurnForAgent(active.id, compoundTurn, { agentName: active.name });
  },
  showToastFn: showToast,
});
initVisionUnits({
  unitsInputEl: visionUnitsInput,
  unitsPerTileInputEl: visionUnitsPerTileInput,
  showToastFn: showToast,
  onUpdatedFn: refreshAfterMutation,
});
initCoordinateMode({
  modeSelectEl: coordinateModeSelect,
  showToastFn: showToast,
  onUpdatedFn: refreshAfterMutation,
});
initDecorations({
  refreshState: (snapshot) => {
    if (snapshot) {
      renderState(snapshot);
    } else {
      void fetchState();
    }
  },
  getSnapshot: () => lastSnapshot,
});
initSettings({ showToastFn: showToast });
initAppTabs();
initLorebooks({
  showToastFn: showToast,
  getActiveAgentIdFn: resolveActiveAgentIdForPrompt,
  onLorebooksChangedFn: () => {
    void reloadPromptLayoutIfOpen();
  },
});
initTemplates({ showToastFn: showToast });
initPlugins({
  showToastFn: showToast,
  onPluginsChangedFn: async (snapshot) => {
    clearHandlerChoicesCache();
    await loadPlayerTurnVerbCatalog();
    await refreshAfterMutation(snapshot);
    await syncPlayerTurnPanel(snapshot ?? lastSnapshot);
  },
});
initGridViewport(gridViewportEl, gridWorldEl);
bindGridContextMenu(gridWorldEl);
if (activeAreaSelect) bindActiveAreaSelect(activeAreaSelect, refreshAfterMutation);
if (activeAgentSelect) bindActiveAgentSelect(activeAgentSelect, refreshAfterMutation);
bindAreaManageButtons({
  createBtn: createAreaBtn,
  editBtn: editAreaBtn,
  deleteBtn: deleteAreaBtn,
  saveAreaBtn: saveAreaTemplateBtn,
  loadAreaBtn: loadAreaTemplateBtn,
});
bindEmitEventButton(emitEventBtn);
bindPromptDebug(promptDebugEl, lastPromptEl, lastPromptEmptyEl, () => getPrompt());
bindResponseDebug(
  responseDebugEl,
  lastResponseEl,
  lastResponseEmptyEl,
  lastResponseTokensEl,
);
initPromptLayout({
  detailsEl: promptLayoutEl,
  listEl: promptBlockListEl,
  statusEl: promptLayoutStatusEl,
  previewEl: promptLayoutPreviewEl,
  previewEmptyEl: promptLayoutPreviewEmptyEl,
  saveBtn: promptLayoutSaveBtn,
  resetBtn: promptLayoutResetBtn,
  refreshPreviewBtn: promptLayoutPreviewBtn,
  addTypeSelect: promptAddTypeSelect,
  addVariantWrap: promptAddVariantWrap,
  addVariantLabel: promptAddVariantLabel,
  addVariantSelect: promptAddVariantSelect,
  addContentWrap: promptAddContentWrap,
  addContentInput: promptAddContentInput,
  addLorebookWrap: document.getElementById("prompt-add-lorebook-wrap"),
  addLorebookIdSelect: document.getElementById("prompt-add-lorebook-id"),
  addBtn: promptAddBtn,
  showToastFn: showToast,
  getActiveAgentIdFn: () => lastSnapshot?.active_agent_id ?? null,
  onPreviewUpdatedFn: async (prompt) => {
    setLastPrompt(prompt);
    if (promptDebugEl.open) {
      renderLastPrompt(lastPromptEl, lastPromptEmptyEl);
    }
    void refreshRunTurnTokenHint();
  },
});

document.getElementById("refresh").addEventListener("click", fetchState);
runTurnBtn.addEventListener("click", runTurn);

if (sessionExportBtn) {
  sessionExportBtn.addEventListener("click", async () => {
    try {
      const { filename } = await exportSession();
      showToast(`Session saved (${filename})`);
      if (statusEl) statusEl.textContent = `Saved ${filename}`;
    } catch (err) {
      showToast(`Save failed: ${err.message}`);
      if (statusEl) statusEl.textContent = `Save failed: ${err.message}`;
    }
  });
}

if (sessionImportBtn && sessionImportInput) {
  sessionImportBtn.addEventListener("click", () => {
    sessionImportInput.click();
  });

  sessionImportInput.addEventListener("change", async () => {
    const file = sessionImportInput.files?.[0];
    sessionImportInput.value = "";
    if (!file) return;
    if (
      !window.confirm(
        "Replace the current session with the loaded file? Unsaved changes will be lost.",
      )
    ) {
      return;
    }
    try {
      const text = await file.text();
      const snapshot = JSON.parse(text);
      const result = await importSession(snapshot);
      setLastPrompt("");
      setLastResponse(null);
      clearTurnLog();
      renderTurnLog(turnLogEl, turnLogEmptyEl);
      await fetchState();
      showToast(result.message || "Session loaded");
      if (statusEl) statusEl.textContent = result.message || "Session loaded";
    } catch (err) {
      showToast(`Load failed: ${err.message}`);
      if (statusEl) statusEl.textContent = `Load failed: ${err.message}`;
    }
  });
}

runTurnBtn.addEventListener("mouseenter", () => {
  void refreshRunTurnTokenHint();
});
async function refreshBanner() {
  if (!subtitleEl) return;
  try {
    const health = await getHealth();
    const studioVersion = health.version || "1.3.1";
    const engineVersion = health.campaign_rpg_engine_version;
    subtitleEl.textContent = engineVersion
      ? `V${studioVersion} — CampAIgn RPG Engine ${engineVersion}`
      : `V${studioVersion} — CampAIgn RPG Engine`;
  } catch {
    // Keep static fallback from index.html.
  }
}

renderTurnLog(turnLogEl, turnLogEmptyEl);
void refreshBanner();
fetchState();
