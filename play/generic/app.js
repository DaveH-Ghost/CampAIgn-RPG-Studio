/**
 * /play/generic — player-scoped grid client (Studio 1.7.5).
 */

import { hasAppearance, resolveAppearanceUrl } from "/static/appearance.js?v=1.7.5f";
import { CELL_SIZE, initGridViewport, maybeCenterGrid } from "/static/gridViewport.js?v=1.7.5f";
import { asArray, isMultiTileObject, objectFootprintSize, objectOccupiesTile } from "/static/snapshot.js?v=1.7.5f";
import {
  buildPlayTurn,
  clearSeatToken,
  fetchPlayerView,
  loadSeatToken,
  postPlayerTurn,
} from "/play/generic/assets/api.js?v=1.7.5f";
import { renderSceneDecorations } from "/play/generic/assets/decorations.js?v=1.7.5f";

const statusEl = document.getElementById("play-status");
const subtitleEl = document.getElementById("play-subtitle");
const noSeatEl = document.getElementById("play-no-seat");
const youEl = document.getElementById("play-you");
const youSheetEl = document.getElementById("play-you-sheet");
const historyEl = document.getElementById("play-history");
const historyEmptyEl = document.getElementById("play-history-empty");
const visionEl = document.getElementById("play-vision");
const inventoryEl = document.getElementById("play-inventory");
const inventoryEmptyEl = document.getElementById("play-inventory-empty");
const gridViewportEl = document.getElementById("grid-viewport");
const gridWorldEl = document.getElementById("grid-world");
const gridEl = document.getElementById("grid");
const gridOverlayEl = document.getElementById("grid-overlay");
const gridViewportBackgroundEl = document.getElementById("grid-viewport-background");
const gridSpritesEl = document.getElementById("grid-sprites");
const gridLinesEl = document.getElementById("grid-lines");
const menuEl = document.getElementById("context-menu");
const toastEl = document.getElementById("toast");
const modalBackdrop = document.getElementById("play-modal-backdrop");
const modalTitle = document.getElementById("play-modal-title");
const modalForm = document.getElementById("play-modal-form");
const modalError = document.getElementById("play-modal-error");
const modalCancel = document.getElementById("play-modal-cancel");
const turnDockEl = document.querySelector(".play-turn-dock");
const composerForm = document.getElementById("play-composer");
const composerMode = document.getElementById("play-composer-mode");
const composerFields = document.getElementById("play-composer-fields");
const composerSay = document.getElementById("play-composer-say");
const composerEmote = document.getElementById("play-composer-emote");
const composerSend = document.getElementById("play-composer-send");
const pendingChipsEl = document.getElementById("play-pending-chips");
const pendingEmptyEl = document.getElementById("play-pending-empty");
const pendingClearBtn = document.getElementById("play-pending-clear");

let seatToken = loadSeatToken();
/** @type {object | null} */
let lastView = null;
let turnBusy = false;
/** @type {EventSource | null} */
let viewStream = null;

/** @type {{ move: { value: string, label: string } | null, look: { value: string, label: string } | null, action: { kind: string, verb: string, target?: string, label: string } | null }} */
let pending = { move: null, look: null, action: null };
/** Which claim on the action slot is newer: queued interact/verb, or typed emote. */
let actionSlotOwner = /** @type {"queue" | "emote" | null} */ (null);

function syncComposerMode() {
  const mode =
    composerMode?.value === "emote" || composerMode?.value === "both"
      ? composerMode.value
      : "say";
  if (composerMode && composerMode.value !== mode) composerMode.value = mode;
  composerFields?.setAttribute("data-mode", mode);
}

function setComposerEnabled(enabled) {
  composerForm?.classList.toggle("is-disabled", !enabled);
  turnDockEl?.classList.toggle("is-disabled", !enabled);
  if (composerMode) composerMode.disabled = !enabled;
  if (composerSay) composerSay.disabled = !enabled;
  if (composerEmote) composerEmote.disabled = !enabled;
  if (composerSend) {
    composerSend.disabled = !enabled;
    composerSend.classList.remove("is-waiting-turn");
    composerSend.title = enabled ? "" : composerSend.title;
  }
  if (pendingClearBtn) pendingClearBtn.disabled = !enabled;
}

function syncActingState(view) {
  const canAct = view?.can_act !== false;
  const active = Boolean(seatToken) && !turnBusy;
  const waiting =
    view?.initiative_enabled && !canAct && view?.initiative_current?.agent_name;
  composerForm?.classList.toggle("is-disabled", !active);
  turnDockEl?.classList.remove("is-disabled");
  if (composerMode) composerMode.disabled = !active;
  if (composerSay) composerSay.disabled = !active;
  if (composerEmote) composerEmote.disabled = !active;
  if (composerSend) {
    const waitingTurn = active && !canAct;
    composerSend.disabled = !active || !canAct;
    composerSend.classList.toggle("is-waiting-turn", waitingTurn);
    composerSend.title = waitingTurn ? "It is not your turn." : "";
  }
  if (pendingClearBtn) pendingClearBtn.disabled = !active;
  if (statusEl) {
    if (waiting) {
      statusEl.textContent = `Waiting for ${view.initiative_current.agent_name}…`;
    } else if (view) {
      statusEl.textContent = `Turn ${view.session_turn ?? "?"} · ${view.area_id ?? ""}`;
    }
  }
}

function truncateChip(text, max = 36) {
  const s = String(text || "").trim();
  if (s.length <= max) return s;
  return `${s.slice(0, max - 1)}…`;
}

function clearPending({ keepText = true } = {}) {
  pending = { move: null, look: null, action: null };
  actionSlotOwner = null;
  if (!keepText) {
    if (composerSay) composerSay.value = "";
    if (composerEmote) composerEmote.value = "";
  }
  renderPending();
}

function renderPending() {
  if (!pendingChipsEl || !pendingEmptyEl || !pendingClearBtn) return;
  pendingChipsEl.innerHTML = "";
  const chips = [];
  if (pending.move) {
    chips.push({ slot: "move", label: `Move · ${pending.move.label}` });
  }
  if (pending.look) {
    chips.push({ slot: "look", label: `Look · ${pending.look.label}` });
  }
  if (pending.action) {
    chips.push({ slot: "action", label: pending.action.label });
  }
  if (!chips.length) {
    pendingEmptyEl.classList.remove("hidden");
    pendingClearBtn.classList.add("hidden");
    return;
  }
  pendingEmptyEl.classList.add("hidden");
  pendingClearBtn.classList.remove("hidden");
  for (const chip of chips) {
    const el = document.createElement("span");
    el.className = "play-pending-chip";
    el.dataset.slot = chip.slot;
    const label = document.createElement("span");
    label.className = "play-pending-chip-label";
    label.textContent = truncateChip(chip.label);
    label.title = chip.label;
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "play-pending-chip-remove";
    remove.setAttribute("aria-label", `Remove ${chip.slot}`);
    remove.textContent = "×";
    remove.addEventListener("click", (e) => {
      e.stopPropagation();
      clearPendingSlot(chip.slot);
    });
    el.appendChild(label);
    el.appendChild(remove);
    pendingChipsEl.appendChild(el);
  }
}

function clearPendingSlot(slot) {
  if (slot === "move") pending.move = null;
  if (slot === "look") pending.look = null;
  if (slot === "action") {
    pending.action = null;
    if (actionSlotOwner === "queue") actionSlotOwner = null;
  }
  renderPending();
}

function queueMove(value, label) {
  pending.move = { value: String(value), label: String(label) };
  renderPending();
}

function queueLook(value, label) {
  pending.look = { value: String(value), label: String(label) };
  renderPending();
}

/**
 * @param {{ kind: "interact" | "verb", verb: string, target?: string, label: string }} spec
 */
function queueAction(spec) {
  if (pending.action && pending.action.label !== spec.label) {
    showToast(`Replaced action with ${spec.label}`);
  }
  const emoteText = String(composerEmote?.value || "").trim();
  if (emoteText) {
    showToast("Queued action replaces emote on Send (unless you edit emote again).");
  }
  pending.action = {
    kind: spec.kind,
    verb: String(spec.verb),
    target: spec.target != null ? String(spec.target) : undefined,
    label: String(spec.label),
  };
  actionSlotOwner = "queue";
  renderPending();
}

function onEmoteEdited() {
  if (String(composerEmote?.value || "").trim()) {
    actionSlotOwner = "emote";
  } else if (actionSlotOwner === "emote") {
    actionSlotOwner = pending.action ? "queue" : null;
  }
}

function showToast(message, isError = false) {
  if (!toastEl) return;
  toastEl.textContent = message;
  toastEl.classList.toggle("toast-error", Boolean(isError));
  toastEl.classList.remove("hidden");
  clearTimeout(showToast._t);
  showToast._t = setTimeout(() => toastEl.classList.add("hidden"), 3200);
}

function hideMenu() {
  menuEl?.classList.add("hidden");
  menuEl && (menuEl.innerHTML = "");
}

function showMenu(x, y, items) {
  if (!menuEl) return;
  menuEl.innerHTML = "";
  for (const item of items) {
    if (item.hidden) continue;
    if (item.sep) {
      const sep = document.createElement("div");
      sep.className = "context-menu-sep";
      menuEl.appendChild(sep);
      continue;
    }
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "context-menu-item";
    btn.textContent = item.label;
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      hideMenu();
      item.action?.();
    });
    menuEl.appendChild(btn);
  }
  menuEl.classList.remove("hidden");
  const pad = 4;
  const mw = menuEl.offsetWidth;
  const mh = menuEl.offsetHeight;
  menuEl.style.left = `${Math.min(x, window.innerWidth - mw - pad)}px`;
  menuEl.style.top = `${Math.min(y, window.innerHeight - mh - pad)}px`;
}

function closeModal() {
  modalBackdrop?.classList.add("hidden");
  if (modalForm) modalForm.innerHTML = "";
  if (modalError) modalError.textContent = "";
}

/**
 * @param {{ title: string, fields: Array<{name:string,label:string,type?:string,options?:Array<{value:string,label:string}>, rows?:number}>, onSubmit: (data: Record<string,string>) => void | Promise<void> }} opts
 */
function openModal({ title, fields, onSubmit }) {
  if (!modalBackdrop || !modalForm || !modalTitle) return;
  modalTitle.textContent = title;
  modalError.textContent = "";
  modalForm.innerHTML = "";
  for (const field of fields) {
    const label = document.createElement("label");
    const span = document.createElement("span");
    span.textContent = field.label;
    label.appendChild(span);
    let input;
    if (field.type === "select") {
      input = document.createElement("select");
      input.name = field.name;
      for (const opt of field.options || []) {
        const o = document.createElement("option");
        o.value = opt.value;
        o.textContent = opt.label;
        input.appendChild(o);
      }
    } else if (field.type === "textarea") {
      input = document.createElement("textarea");
      input.name = field.name;
      input.rows = field.rows || 3;
    } else {
      input = document.createElement("input");
      input.type = "text";
      input.name = field.name;
    }
    label.appendChild(input);
    modalForm.appendChild(label);
  }
  modalForm.onsubmit = async (e) => {
    e.preventDefault();
    const data = {};
    for (const field of fields) {
      const el = modalForm.elements.namedItem(field.name);
      data[field.name] = el && "value" in el ? String(el.value) : "";
    }
    try {
      modalError.textContent = "";
      await onSubmit(data);
      closeModal();
    } catch (err) {
      modalError.textContent = String(err.message || err);
    }
  };
  modalBackdrop.classList.remove("hidden");
}

function viewAsSnapshot(view) {
  const areaId = view.area_id;
  return {
    active_area_id: areaId,
    active_agent_id: view.agent_id,
    session_turn: view.session_turn,
    areas: {
      [areaId]: {
        grid: view.grid,
        area_description: view.area_description || "",
        objects: asArray(view.objects),
        decorations: asArray(view.decorations),
        recent_events: asArray(view.recent_events),
      },
    },
    agents: asArray(view.agents).map((a) => ({
      ...a,
      area_id: a.area_id || areaId,
    })),
  };
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
        if (dx !== 0 || dy !== 0) covered.add(posKey(ax + dx, ay + dy));
      }
    }
  }
  return covered;
}

function createNameChip(entity, kind, isActive) {
  const chip = document.createElement("div");
  chip.className = `chip chip-${kind}${isActive ? " chip-active" : ""}`;
  chip.dataset.kind = kind;
  chip.dataset.id = entity.id;
  chip.title = entity.name;
  chip.textContent = entity.name;
  return chip;
}

function createTokenMarker(entity, kind, isActive) {
  const token = document.createElement("div");
  token.className = `token token-${kind}${isActive ? " token-active" : ""}`;
  token.dataset.kind = kind;
  token.dataset.id = entity.id;
  token.title = entity.name;
  const img = document.createElement("img");
  img.className = "token-img";
  img.src = resolveAppearanceUrl(entity.appearance);
  img.alt = entity.name;
  img.draggable = false;
  img.addEventListener("error", () => {
    token.replaceWith(createNameChip(entity, kind, isActive));
  });
  token.appendChild(img);
  return token;
}

function createEntityMarker(entity, kind, isActive) {
  return hasAppearance(entity)
    ? createTokenMarker(entity, kind, isActive)
    : createNameChip(entity, kind, isActive);
}

function createFootprintMarker(entity, kind, grid, isActive = false) {
  const marker = document.createElement("div");
  marker.className = `footprint-marker footprint-marker-${kind}${isActive ? " footprint-marker-active" : ""}`;
  marker.dataset.kind = kind;
  marker.dataset.id = entity.id;
  marker.title = entity.name;
  const { width, height } =
    kind === "agent" ? { width: 1, height: 1 } : objectFootprintSize(entity);
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

function renderGrid(view) {
  const snap = viewAsSnapshot(view);
  const areaId = view.area_id;
  const block = snap.areas[areaId];
  const grid = block?.grid;
  if (!grid) {
    gridEl.innerHTML = "";
    gridOverlayEl.innerHTML = "";
    gridEl.classList.add("grid-empty");
    return;
  }
  gridEl.classList.remove("grid-empty");
  const objects = asArray(view.objects);
  const agents = asArray(view.agents);
  const footprintCover = buildFootprintCoverKeys(objects);
  const width = grid.max_x - grid.min_x + 1;
  const height = grid.max_y - grid.min_y + 1;
  const pixelWidth = width * CELL_SIZE;
  const pixelHeight = height * CELL_SIZE;

  gridEl.style.setProperty("--grid-cols", String(width));
  gridEl.style.setProperty("--grid-rows", String(height));
  gridEl.style.width = `${pixelWidth}px`;
  gridEl.style.height = `${pixelHeight}px`;
  gridEl.innerHTML = "";
  gridOverlayEl.innerHTML = "";
  gridOverlayEl.style.width = `${pixelWidth}px`;
  gridOverlayEl.style.height = `${pixelHeight}px`;

  for (let y = grid.min_y; y <= grid.max_y; y++) {
    for (let x = grid.min_x; x <= grid.max_x; x++) {
      const tile = document.createElement("div");
      tile.className = "tile";
      if (footprintCover.has(posKey(x, y))) tile.classList.add("tile-covered");
      tile.dataset.x = String(x);
      tile.dataset.y = String(y);
      const coord = document.createElement("span");
      coord.className = "tile-coord";
      coord.textContent = `${x},${y}`;
      tile.appendChild(coord);
      gridEl.appendChild(tile);
    }
  }

  for (const object of objects) {
    gridOverlayEl.appendChild(createFootprintMarker(object, "object", grid));
  }
  for (const agent of agents) {
    gridOverlayEl.appendChild(
      createFootprintMarker(agent, "agent", grid, agent.id === view.agent_id),
    );
  }

  renderSceneDecorations(
    {
      grid,
      decorations: asArray(view.decorations),
    },
    {
      gridViewportBackgroundEl,
      gridSpritesEl,
      gridLinesEl,
      gridEl,
    },
  );
  maybeCenterGrid(gridEl);
}

function historyMeta(entry) {
  if (entry.source === "you") {
    const kinds = asArray(entry.kinds).filter(Boolean);
    const kindLabel =
      kinds.length > 1
        ? kinds.join(" · ")
        : entry.kind && entry.kind !== "compound"
          ? entry.kind
          : kinds[0] || "";
    const kind = kindLabel ? ` · ${kindLabel}` : "";
    return `You${entry.turn != null ? ` · turn ${entry.turn}` : ""}${kind}`;
  }
  if (entry.source === "event") {
    return entry.turn != null ? `Event · session ${entry.turn}` : "Event";
  }
  const who = entry.actor_name || "Someone";
  return entry.turn != null ? `${who} · session ${entry.turn}` : who;
}

function renderHistory(view, { forceScroll = false } = {}) {
  if (!historyEl || !historyEmptyEl) return;
  const entries = asArray(view.history).filter((e) => String(e?.text || "").trim());
  const stickBottom =
    forceScroll ||
    historyEl.scrollHeight - historyEl.scrollTop - historyEl.clientHeight < 48;
  historyEl.innerHTML = "";
  if (!entries.length) {
    historyEmptyEl.classList.remove("hidden");
    return;
  }
  historyEmptyEl.classList.add("hidden");
  for (const entry of entries) {
    const li = document.createElement("li");
    li.className = `play-history-item ${entry.source || "witness"}`;
    const meta = document.createElement("span");
    meta.className = "play-history-meta";
    meta.textContent = historyMeta(entry);
    li.appendChild(meta);
    li.appendChild(document.createTextNode(String(entry.text).trim()));
    historyEl.appendChild(li);
  }
  if (stickBottom) {
    historyEl.scrollTop = historyEl.scrollHeight;
  }
}

function renderYouSheet(view) {
  if (!youSheetEl) return;
  const stats = asArray(view.stats);
  const skills = asArray(view.skills);
  youSheetEl.innerHTML = "";
  if (!stats.length && !skills.length) {
    youSheetEl.classList.add("hidden");
    return;
  }
  youSheetEl.classList.remove("hidden");

  if (stats.length) {
    const heading = document.createElement("p");
    heading.className = "play-you-sheet-heading";
    heading.textContent = "Stats";
    youSheetEl.appendChild(heading);
    const ul = document.createElement("ul");
    ul.className = "play-you-stats";
    for (const row of stats) {
      const li = document.createElement("li");
      const mod = Number(row.mod) || 0;
      const modText = mod >= 0 ? `+${mod}` : `${mod}`;
      li.textContent = `${row.name} ${row.score} (${modText})`;
      ul.appendChild(li);
    }
    youSheetEl.appendChild(ul);
  }

  const skillsHeading = document.createElement("p");
  skillsHeading.className = "play-you-sheet-heading";
  skillsHeading.textContent = "Skills";
  youSheetEl.appendChild(skillsHeading);
  if (!skills.length) {
    const empty = document.createElement("p");
    empty.className = "play-meta";
    empty.textContent = "(none)";
    youSheetEl.appendChild(empty);
    return;
  }
  const skillsList = document.createElement("ul");
  skillsList.className = "play-you-skills";
  for (const row of skills) {
    const li = document.createElement("li");
    li.textContent = `${row.name} ${row.level}`;
    skillsList.appendChild(li);
  }
  youSheetEl.appendChild(skillsList);
}

function renderSidebar(view, opts = {}) {
  youEl.textContent = `${view.agent_name} (${view.agent_id}) — ${view.area_id} — turn ${view.session_turn ?? "?"}`;
  if (view.hp != null) {
    const maxPart = view.max_hp != null ? `/${view.max_hp}` : "";
    youEl.textContent += ` — HP ${view.hp}${maxPart}`;
  }
  renderYouSheet(view);
  visionEl.textContent = view.passive_vision || "(no vision text)";
  subtitleEl.textContent = `Playing as ${view.agent_name}`;
  renderHistory(view, opts);

  const assist = asArray(view.assist);
  inventoryEl.innerHTML = "";
  if (!assist.length) {
    inventoryEmptyEl.classList.remove("hidden");
  } else {
    inventoryEmptyEl.classList.add("hidden");
    for (const item of assist) {
      const li = document.createElement("li");
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = item.label || item.id;
      btn.addEventListener("contextmenu", (e) => {
        e.preventDefault();
        e.stopPropagation();
        showInventoryMenu(e.clientX, e.clientY, item);
      });
      btn.addEventListener("click", (e) => {
        showInventoryMenu(e.clientX, e.clientY, item);
      });
      li.appendChild(btn);
      inventoryEl.appendChild(li);
    }
  }
}

function renderView(view, opts = {}) {
  try {
    lastView = view;
    renderGrid(view);
    renderSidebar(view, opts);
    syncActingState(view);
  } catch (err) {
    console.error(err);
    statusEl.textContent = `Render failed: ${err?.message || err}`;
    throw err;
  }
}

async function submitTurn(compoundTurn) {
  if (!seatToken || turnBusy) return;
  turnBusy = true;
  setComposerEnabled(false);
  statusEl.textContent = "Submitting turn…";
  try {
    const result = await postPlayerTurn(seatToken, compoundTurn);
    if (!result.ok) {
      if (result.concurrency_limit_exceeded) {
        showToast(
          "LLM concurrency limit — ask the GM to undo and turn off Concurrent LLM calls in Settings.",
          true,
        );
        statusEl.textContent = "Concurrency limit";
        return;
      }
      throw new Error(result.message || "Turn failed.");
    }
    clearPending({ keepText: false });
    if (result.view) renderView(result.view, { forceScroll: true });
    const lines = asArray(result.steps)
      .map((step) => String(step?.result || "").trim())
      .filter(Boolean);
    showToast(lines.length ? lines.join(" · ") : result.message || "Turn applied.");
    if (result.view) syncActingState(result.view);
  } catch (err) {
    if (err.code === 401) {
      clearSeatToken();
      seatToken = null;
      noSeatEl.classList.remove("hidden");
      statusEl.textContent = "Seat expired";
      setComposerEnabled(false);
    }
    if (err.concurrency_limit_exceeded) {
      showToast(
        "LLM concurrency limit — ask the GM to undo and turn off Concurrent LLM calls in Settings.",
        true,
      );
      statusEl.textContent = "Concurrency limit";
      return;
    }
    showToast(String(err.message || err), true);
    throw err;
  } finally {
    turnBusy = false;
    if (seatToken && lastView) syncActingState(lastView);
    else if (!seatToken) setComposerEnabled(false);
  }
}

function composerModeValue() {
  const mode = composerMode?.value;
  if (mode === "emote" || mode === "both") return mode;
  return "say";
}

function visibleSayText() {
  const mode = composerModeValue();
  if (mode === "emote") return "";
  return String(composerSay?.value || "").trim();
}

function visibleEmoteText() {
  const mode = composerModeValue();
  if (mode === "say") return "";
  return String(composerEmote?.value || "").trim();
}

function buildQueuedCompoundTurn() {
  const say = visibleSayText();
  const emote = visibleEmoteText();
  const useEmote = Boolean(emote) && (actionSlotOwner !== "queue" || !pending.action);
  const useQueuedAction = Boolean(pending.action) && (!emote || actionSlotOwner === "queue");

  if (emote && pending.action && actionSlotOwner === "emote") {
    showToast(`Using emote; dropped ${pending.action.label}.`);
  } else if (emote && pending.action && actionSlotOwner === "queue") {
    showToast(`Using ${pending.action.label}; emote ignored (action slot).`);
  }

  /** @type {Parameters<typeof buildPlayTurn>[0]} */
  const opts = { reasoning: "Player turn." };
  if (pending.move) opts.move = pending.move.value;
  if (pending.look) opts.look = pending.look.value;
  if (say) opts.say = say;

  if (useEmote) {
    opts.action = "emote";
    opts.verb = emote;
  } else if (useQueuedAction && pending.action) {
    opts.action = pending.action.kind;
    opts.verb = pending.action.verb;
    if (pending.action.target) opts.target = pending.action.target;
  } else {
    opts.action = "none";
  }

  const hasContent =
    Boolean(opts.move) ||
    Boolean(opts.look) ||
    Boolean(opts.say) ||
    opts.action !== "none";
  return { opts, hasContent };
}

async function submitComposer() {
  if (!seatToken || turnBusy) return;
  if (lastView?.can_act === false) {
    showToast(lastView.wait_reason || "It is not your turn.", true);
    return;
  }
  const { opts, hasContent } = buildQueuedCompoundTurn();
  if (!hasContent) {
    showToast("Queue a move/look/action or enter say/emote text.", true);
    return;
  }
  try {
    await submitTurn(buildPlayTurn(opts));
    composerSay?.focus();
  } catch {
    /* toast already shown */
  }
}

function enabledActions(object) {
  const detail = object.actions_detail || {};
  const names = asArray(object.actions);
  return names.filter((name) => {
    const meta = detail[name];
    if (!meta) return true;
    if (meta.kind === "trigger") return false;
    if (meta.enabled === false) return false;
    return true;
  });
}

function showTileMenu(x, y, tileX, tileY) {
  showMenu(x, y, [
    {
      label: `Move to ${tileX},${tileY}`,
      action: () => queueMove(`${tileX},${tileY}`, `${tileX},${tileY}`),
    },
  ]);
}

function showObjectMenu(x, y, object) {
  const items = [
    {
      label: `Move to ${object.name}`,
      action: () => queueMove(object.id, object.name),
    },
    {
      label: `Look at ${object.name}`,
      action: () => queueLook(object.id, object.name),
    },
    { sep: true },
  ];
  for (const actionName of enabledActions(object)) {
    items.push({
      label: actionName,
      action: () =>
        queueAction({
          kind: "interact",
          target: object.id,
          verb: actionName,
          label: `${actionName} · ${object.name}`,
        }),
    });
  }
  showMenu(x, y, items);
}

function showAgentMenu(x, y, agent) {
  const items = [];
  if (agent.id !== lastView?.agent_id) {
    items.push({
      label: `Move to ${agent.name}`,
      action: () => queueMove(agent.id, agent.name),
    });
    items.push({
      label: `Look at ${agent.name}`,
      action: () => queueLook(agent.id, agent.name),
    });
  } else {
    items.push({ label: "(you)", action: () => {}, hidden: false });
  }
  showMenu(x, y, items);
}

function showInventoryMenu(x, y, item) {
  const verbs = asArray(item.verbs);
  const items = verbs.map((verb) => {
    if (verb === "give" || verb === "show") {
      return {
        label: verb,
        action: () => openSocialModal(verb, item),
      };
    }
    return {
      label: verb,
      action: () =>
        queueAction({
          kind: "verb",
          verb,
          target: item.id,
          label: `${verb} · ${item.label || item.id}`,
        }),
    };
  });
  if (!items.length) {
    items.push({ label: "(no actions)", action: () => {} });
  }
  showMenu(x, y, items);
}

function openSocialModal(verb, item) {
  const candidates = asArray(lastView?.social_candidates);
  if (!candidates.length) {
    showToast("No agents in give/show reach this turn (move closer).", true);
    return;
  }
  openModal({
    title: `${verb} ${item.label || item.id}`,
    fields: [
      {
        name: "agent_id",
        label: "Agent",
        type: "select",
        options: candidates.map((c) => ({
          value: c.id,
          label: `${c.name} (${c.id})`,
        })),
      },
    ],
    onSubmit: async (data) => {
      const agent = candidates.find((c) => c.id === data.agent_id);
      queueAction({
        kind: "verb",
        verb,
        target: `${data.agent_id} ${item.id}`,
        label: `${verb} · ${item.label || item.id} → ${agent?.name || data.agent_id}`,
      });
    },
  });
}

function tileCoordsFromEvent(e) {
  const tile = e.target?.closest?.(".tile, .tile-line");
  if (tile?.dataset?.x != null) {
    return { x: Number(tile.dataset.x), y: Number(tile.dataset.y) };
  }
  const grid = lastView?.grid;
  if (!grid || !gridEl) return null;
  const rect = gridEl.getBoundingClientRect();
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

function entitiesAt(tileX, tileY) {
  const agents = asArray(lastView?.agents).filter(
    (a) => Array.isArray(a.position) && a.position[0] === tileX && a.position[1] === tileY,
  );
  const objects = asArray(lastView?.objects).filter((o) => objectOccupiesTile(o, tileX, tileY));
  return { agents, objects };
}

function showStackedTileMenu(x, y, tileX, tileY, at) {
  const items = [
    {
      label: `Move to ${tileX},${tileY}`,
      action: () => queueMove(`${tileX},${tileY}`, `${tileX},${tileY}`),
    },
    { sep: true },
  ];
  for (const agent of at.agents) {
    items.push({
      label: `Agent: ${agent.name}`,
      action: () => showAgentMenu(x, y, agent),
    });
  }
  for (const object of at.objects) {
    items.push({
      label: `Object: ${object.name}`,
      action: () => showObjectMenu(x, y, object),
    });
  }
  showMenu(x, y, items);
}

function onGridContextMenu(e) {
  e.preventDefault();
  hideMenu();
  if (!lastView) return;
  const tile = tileCoordsFromEvent(e);
  if (!tile) return;
  const at = entitiesAt(tile.x, tile.y);
  const count = at.agents.length + at.objects.length;
  if (count > 1) {
    showStackedTileMenu(e.clientX, e.clientY, tile.x, tile.y, at);
    return;
  }
  if (count === 1) {
    if (at.agents[0]) {
      showAgentMenu(e.clientX, e.clientY, at.agents[0]);
      return;
    }
    if (at.objects[0]) {
      showObjectMenu(e.clientX, e.clientY, at.objects[0]);
      return;
    }
  }
  showTileMenu(e.clientX, e.clientY, tile.x, tile.y);
}

function stopViewStream() {
  if (viewStream) {
    viewStream.close();
    viewStream = null;
  }
}

function startViewStream() {
  stopViewStream();
  if (!seatToken || typeof EventSource === "undefined") return;
  const url = `/api/player/stream?seat=${encodeURIComponent(seatToken)}`;
  viewStream = new EventSource(url);
  viewStream.addEventListener("change", () => {
    if (turnBusy) return;
    void refreshView({ quiet: true });
  });
  viewStream.onerror = () => {
    // EventSource reconnects automatically; surface only if seat is gone.
  };
}

async function refreshView({ quiet = false } = {}) {
  if (!seatToken) return;
  if (!quiet) statusEl.textContent = "Loading…";
  try {
    const view = await fetchPlayerView(seatToken);
    renderView(view);
    noSeatEl.classList.add("hidden");
  } catch (err) {
    if (err.code === 401) {
      stopViewStream();
      clearSeatToken();
      seatToken = null;
      noSeatEl.classList.remove("hidden");
      statusEl.textContent = "Seat expired";
      setComposerEnabled(false);
      return;
    }
    if (!quiet) showToast(String(err.message || err), true);
    statusEl.textContent = String(err.message || err);
  }
}

try {
  initGridViewport(gridViewportEl, gridWorldEl);
  syncComposerMode();
  renderPending();
  document.addEventListener("click", () => hideMenu());
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      hideMenu();
      closeModal();
      if (
        document.activeElement === composerSay ||
        document.activeElement === composerEmote
      ) {
        /** @type {HTMLElement} */ (document.activeElement).blur();
      }
    }
  });
  modalCancel?.addEventListener("click", closeModal);
  modalBackdrop?.addEventListener("click", (e) => {
    if (e.target === modalBackdrop) closeModal();
  });
  gridWorldEl?.addEventListener("contextmenu", onGridContextMenu);
  composerMode?.addEventListener("change", syncComposerMode);
  composerEmote?.addEventListener("input", onEmoteEdited);
  pendingClearBtn?.addEventListener("click", () => clearPending({ keepText: true }));
  composerForm?.addEventListener("submit", (e) => {
    e.preventDefault();
    void submitComposer();
  });

  if (!seatToken) {
    noSeatEl.classList.remove("hidden");
    statusEl.textContent = "No seat";
    setComposerEnabled(false);
  } else {
    void refreshView().then(() => startViewStream());
  }
} catch (err) {
  console.error(err);
  if (statusEl) statusEl.textContent = `Boot failed: ${err?.message || err}`;
}
