/**
 * Scene decorations — render layers and edit-scene UI (V1.3.0).
 */

import {
  deleteDecoration,
  postCreateDecoration,
  reorderDecoration,
  updateDecoration,
  uploadDecorationAsset,
} from "./api.js";
import { resolveAppearanceUrl } from "./appearance.js";
import { CELL_SIZE } from "./gridViewport.js";
import { activeAreaView, asArray } from "./snapshot.js";

let editSceneMode = false;
let selectedDecorationId = null;
let onStateRefresh = null;
let getSnapshot = () => null;
let dragState = null;
let resizeState = null;

const MIN_SPRITE_SIZE = 1;
const RESIZE_HANDLES = ["nw", "ne", "sw", "se"];

const editToggleEl = () => document.getElementById("edit-scene-toggle");
const panelEl = () => document.getElementById("scene-decorations-panel");
const listEl = () => document.getElementById("scene-decorations-list");
const emptyEl = () => document.getElementById("scene-decorations-empty");
const detailEl = () => document.getElementById("scene-decoration-detail");

export function isSceneEditMode() {
  return editSceneMode;
}

export function getSelectedDecorationId() {
  return selectedDecorationId;
}

export function initDecorations({ refreshState, getSnapshot: getSnapshotFn }) {
  onStateRefresh = refreshState;
  getSnapshot = getSnapshotFn ?? (() => null);
  const toggle = editToggleEl();
  toggle?.addEventListener("click", () => {
    editSceneMode = !editSceneMode;
    syncEditSceneUi();
    if (onStateRefresh) {
      onStateRefresh();
    }
  });

  document.getElementById("scene-add-sprite")?.addEventListener("click", () => {
    void addSpriteDecoration();
  });
  document.getElementById("scene-add-background")?.addEventListener("click", () => {
    void addBackgroundDecoration();
  });
  document.getElementById("scene-decoration-delete")?.addEventListener("click", () => {
    void deleteSelectedDecoration();
  });
  document.getElementById("scene-decoration-up")?.addEventListener("click", () => {
    void reorderSelected("up");
  });
  document.getElementById("scene-decoration-down")?.addEventListener("click", () => {
    void reorderSelected("down");
  });
  document.getElementById("scene-decoration-apply")?.addEventListener("click", () => {
    void applyDetailForm();
  });
  document.getElementById("scene-decoration-browse")?.addEventListener("click", () => {
    void browseDecorationImageForDetail();
  });

  syncEditSceneUi();
}

function syncEditSceneUi() {
  const toggle = editToggleEl();
  const panel = panelEl();
  const viewport = document.getElementById("grid-viewport");
  if (toggle) {
    toggle.classList.toggle("active", editSceneMode);
    toggle.setAttribute("aria-pressed", editSceneMode ? "true" : "false");
  }
  panel?.classList.toggle("hidden", !editSceneMode);
  viewport?.classList.toggle("scene-edit-mode", editSceneMode);
  if (!editSceneMode) {
    selectedDecorationId = null;
    dragState = null;
    resizeState = null;
  }
}

function sortedDecorations(decorations) {
  return [...asArray(decorations)].sort((a, b) => {
    if (a.kind === "background" && b.kind !== "background") return -1;
    if (b.kind === "background" && a.kind !== "background") return 1;
    return (a.z_index ?? 0) - (b.z_index ?? 0) || String(a.id).localeCompare(String(b.id));
  });
}

export function renderSceneDecorations(view, elements) {
  const { gridViewportBackgroundEl, gridSpritesEl, gridLinesEl, gridEl } = elements;
  const { grid } = view;
  if (!grid || !gridSpritesEl) {
    if (gridViewportBackgroundEl) gridViewportBackgroundEl.innerHTML = "";
    if (gridSpritesEl) gridSpritesEl.innerHTML = "";
    if (gridLinesEl) gridLinesEl.innerHTML = "";
    return;
  }

  const width = grid.max_x - grid.min_x + 1;
  const height = grid.max_y - grid.min_y + 1;
  const pixelWidth = width * CELL_SIZE;
  const pixelHeight = height * CELL_SIZE;

  for (const el of [gridSpritesEl, gridLinesEl]) {
    if (!el) continue;
    el.style.width = `${pixelWidth}px`;
    el.style.height = `${pixelHeight}px`;
    el.style.setProperty("--grid-cols", String(width));
    el.style.setProperty("--grid-rows", String(height));
  }

  if (gridViewportBackgroundEl) {
    gridViewportBackgroundEl.innerHTML = "";
    const background = sortedDecorations(view.decorations).find((d) => d.kind === "background");
    if (background) {
      gridViewportBackgroundEl.appendChild(createViewportBackgroundElement(background));
    }
  }

  gridSpritesEl.innerHTML = "";

  for (const decoration of sortedDecorations(view.decorations)) {
    if (decoration.kind !== "background") {
      gridSpritesEl.appendChild(createSpriteElement(decoration));
    }
  }

  if (gridLinesEl) {
    gridLinesEl.innerHTML = "";
    for (let y = grid.min_y; y <= grid.max_y; y++) {
      for (let x = grid.min_x; x <= grid.max_x; x++) {
        const tile = document.createElement("div");
        tile.className = "tile tile-line";
        tile.dataset.x = String(x);
        tile.dataset.y = String(y);
        gridLinesEl.appendChild(tile);
      }
    }
  }

  if (gridEl) {
    gridEl.classList.toggle("grid-with-lines-layer", Boolean(gridLinesEl));
  }

  renderDecorationsPanel(view);
}

function getSpriteElement(decorationId) {
  return document.querySelector(
    `.scene-decoration-sprite[data-decoration-id="${CSS.escape(decorationId)}"]`,
  );
}

function applySpriteGeometry(el, { x, y, width, height }) {
  if (!el) return;
  el.style.left = `${x}px`;
  el.style.top = `${y}px`;
  el.style.width = `${width}px`;
  el.style.height = `${height}px`;
}

function syncDetailFormGeometry({ x, y, width, height }) {
  const xInput = document.getElementById("scene-decoration-x");
  const yInput = document.getElementById("scene-decoration-y");
  const widthInput = document.getElementById("scene-decoration-width");
  const heightInput = document.getElementById("scene-decoration-height");
  if (xInput && x !== undefined) xInput.value = String(x);
  if (yInput && y !== undefined) yInput.value = String(y);
  if (widthInput && width !== undefined) widthInput.value = String(width);
  if (heightInput && height !== undefined) heightInput.value = String(height);
}

function computeResizedGeometry(corner, origin, dx, dy) {
  let { x, y, width, height } = origin;
  switch (corner) {
    case "se":
      width = Math.max(MIN_SPRITE_SIZE, origin.width + dx);
      height = Math.max(MIN_SPRITE_SIZE, origin.height + dy);
      break;
    case "sw":
      width = Math.max(MIN_SPRITE_SIZE, origin.width - dx);
      height = Math.max(MIN_SPRITE_SIZE, origin.height + dy);
      x = origin.x + origin.width - width;
      break;
    case "ne":
      width = Math.max(MIN_SPRITE_SIZE, origin.width + dx);
      height = Math.max(MIN_SPRITE_SIZE, origin.height - dy);
      y = origin.y + origin.height - height;
      break;
    case "nw":
      width = Math.max(MIN_SPRITE_SIZE, origin.width - dx);
      height = Math.max(MIN_SPRITE_SIZE, origin.height - dy);
      x = origin.x + origin.width - width;
      y = origin.y + origin.height - height;
      break;
    default:
      break;
  }
  return { x, y, width, height };
}

function backgroundSizeCss(width, height) {
  const w = Number(width) || 0;
  const h = Number(height) || 0;
  if (w > 0 && h > 0) return `${w}px ${h}px`;
  if (w > 0) return `${w}px auto`;
  if (h > 0) return `auto ${h}px`;
  return "auto";
}

function parseBackgroundTileDim(value) {
  const trimmed = String(value ?? "").trim();
  if (!trimmed) return 0;
  const parsed = Number.parseInt(trimmed, 10);
  return Number.isNaN(parsed) ? 0 : Math.max(0, parsed);
}

function createViewportBackgroundElement(decoration) {
  const el = document.createElement("div");
  el.className = "scene-decoration scene-decoration-viewport-background";
  el.dataset.decorationId = decoration.id;
  const url = resolveAppearanceUrl(decoration.image);
  el.style.backgroundImage = url ? `url("${url}")` : "";
  el.style.backgroundRepeat = decoration.repeat || "repeat";
  el.style.backgroundSize = backgroundSizeCss(decoration.width, decoration.height);
  el.style.backgroundPosition = "0 0";
  return el;
}

function createSpriteElement(decoration) {
  const el = document.createElement("div");
  el.className = "scene-decoration scene-decoration-sprite";
  el.dataset.decorationId = decoration.id;
  if (selectedDecorationId === decoration.id && editSceneMode) {
    el.classList.add("selected");
  }
  const url = resolveAppearanceUrl(decoration.image);
  el.style.left = `${decoration.x ?? 0}px`;
  el.style.top = `${decoration.y ?? 0}px`;
  el.style.width = `${decoration.width ?? CELL_SIZE}px`;
  el.style.height = `${decoration.height ?? CELL_SIZE}px`;
  el.style.zIndex = String(decoration.z_index ?? 0);
  if (url) {
    const img = document.createElement("img");
    img.src = url;
    img.alt = "";
    img.draggable = false;
    el.appendChild(img);
  }
  if (editSceneMode) {
    el.style.pointerEvents = "auto";
    el.addEventListener("pointerdown", (event) => onSpritePointerDown(event, decoration));
    if (selectedDecorationId === decoration.id) {
      for (const corner of RESIZE_HANDLES) {
        const handle = document.createElement("div");
        handle.className = `scene-decoration-resize-handle ${corner}`;
        handle.dataset.corner = corner;
        handle.addEventListener("pointerdown", (event) => {
          onResizePointerDown(event, decoration, corner);
        });
        el.appendChild(handle);
      }
    }
  }
  return el;
}

function onResizePointerDown(event, decoration, corner) {
  if (!editSceneMode || event.button !== 0) return;
  event.preventDefault();
  event.stopPropagation();
  selectedDecorationId = decoration.id;
  resizeState = {
    id: decoration.id,
    corner,
    startX: event.clientX,
    startY: event.clientY,
    origin: {
      x: decoration.x ?? 0,
      y: decoration.y ?? 0,
      width: decoration.width ?? CELL_SIZE,
      height: decoration.height ?? CELL_SIZE,
    },
    moved: false,
  };
  const onMove = (moveEvent) => {
    if (!resizeState) return;
    const dx = moveEvent.clientX - resizeState.startX;
    const dy = moveEvent.clientY - resizeState.startY;
    if (Math.abs(dx) > 2 || Math.abs(dy) > 2) {
      resizeState.moved = true;
    }
    const geometry = computeResizedGeometry(resizeState.corner, resizeState.origin, dx, dy);
    applySpriteGeometry(getSpriteElement(resizeState.id), geometry);
    syncDetailFormGeometry(geometry);
  };
  const onUp = async () => {
    window.removeEventListener("pointermove", onMove);
    window.removeEventListener("pointerup", onUp);
    const state = resizeState;
    resizeState = null;
    if (!state) return;
    if (!state.moved) {
      renderDecorationsPanel(activeAreaView(getSnapshot()));
      if (onStateRefresh) onStateRefresh();
      return;
    }
    const el = getSpriteElement(state.id);
    const payload = {
      decoration_id: state.id,
      x: el ? Number.parseInt(el.style.left, 10) : state.origin.x,
      y: el ? Number.parseInt(el.style.top, 10) : state.origin.y,
      width: el ? Number.parseInt(el.style.width, 10) : state.origin.width,
      height: el ? Number.parseInt(el.style.height, 10) : state.origin.height,
    };
    try {
      const data = await updateDecoration(payload);
      if (data.snapshot && onStateRefresh) onStateRefresh(data.snapshot);
    } catch (err) {
      alert(err.message || String(err));
      if (onStateRefresh) onStateRefresh();
    }
  };
  window.addEventListener("pointermove", onMove);
  window.addEventListener("pointerup", onUp);
}

function onSpritePointerDown(event, decoration) {
  if (!editSceneMode || event.button !== 0) return;
  if (event.target?.classList?.contains("scene-decoration-resize-handle")) return;
  event.preventDefault();
  event.stopPropagation();
  selectedDecorationId = decoration.id;
  dragState = {
    id: decoration.id,
    startX: event.clientX,
    startY: event.clientY,
    originX: decoration.x ?? 0,
    originY: decoration.y ?? 0,
    moved: false,
  };
  const onMove = (moveEvent) => {
    if (!dragState) return;
    const dx = moveEvent.clientX - dragState.startX;
    const dy = moveEvent.clientY - dragState.startY;
    if (Math.abs(dx) > 2 || Math.abs(dy) > 2) {
      dragState.moved = true;
    }
    const el = getSpriteElement(dragState.id);
    if (el) {
      applySpriteGeometry(el, {
        x: dragState.originX + dx,
        y: dragState.originY + dy,
        width: Number.parseInt(el.style.width, 10) || decoration.width || CELL_SIZE,
        height: Number.parseInt(el.style.height, 10) || decoration.height || CELL_SIZE,
      });
    }
  };
  const onUp = async () => {
    window.removeEventListener("pointermove", onMove);
    window.removeEventListener("pointerup", onUp);
    const state = dragState;
    dragState = null;
    if (!state) return;
    if (!state.moved) {
      renderDecorationsPanel(activeAreaView(getSnapshot()));
      if (onStateRefresh) onStateRefresh();
      return;
    }
    const el = getSpriteElement(state.id);
    const newX = el ? Number.parseInt(el.style.left, 10) || state.originX : state.originX;
    const newY = el ? Number.parseInt(el.style.top, 10) || state.originY : state.originY;
    syncDetailFormGeometry({ x: newX, y: newY });
    try {
      const data = await updateDecoration({
        decoration_id: state.id,
        x: newX,
        y: newY,
      });
      if (data.snapshot && onStateRefresh) onStateRefresh(data.snapshot);
    } catch (err) {
      alert(err.message || String(err));
      if (onStateRefresh) onStateRefresh();
    }
  };
  window.addEventListener("pointermove", onMove);
  window.addEventListener("pointerup", onUp);
}

function decorationListLabel(decoration) {
  if (decoration.kind === "background") {
    return `Background — ${decoration.image}`;
  }
  const filename =
    String(decoration.image ?? "")
      .split("/")
      .pop() ?? "";
  const stem = filename.replace(/\.[^.]+$/, "") || decoration.id;
  return `Sprite — ${stem}`;
}

function renderDecorationsPanel(view) {
  const list = listEl();
  const empty = emptyEl();
  const detail = detailEl();
  if (!list || !empty) return;

  const decorations = sortedDecorations(view.decorations);
  if (!editSceneMode) {
    list.innerHTML = "";
    empty.classList.add("hidden");
    detail?.classList.add("hidden");
    return;
  }

  if (decorations.length === 0) {
    list.innerHTML = "";
    empty.classList.remove("hidden");
    detail?.classList.add("hidden");
    return;
  }

  empty.classList.add("hidden");
  list.innerHTML = decorations
    .map((decoration) => {
      const selected = decoration.id === selectedDecorationId ? " selected" : "";
      const label = decorationListLabel(decoration);
      return `<li><button type="button" class="scene-decoration-item${selected}" data-id="${escapeAttr(decoration.id)}">${escapeHtml(label)}</button></li>`;
    })
    .join("");

  list.querySelectorAll(".scene-decoration-item").forEach((btn) => {
    btn.addEventListener("click", () => {
      selectedDecorationId = btn.dataset.id ?? null;
      if (onStateRefresh) onStateRefresh();
    });
  });

  const selected = decorations.find((d) => d.id === selectedDecorationId) ?? decorations[0];
  if (!selectedDecorationId && selected) {
    selectedDecorationId = selected.id;
  }
  renderDetailForm(selected);
}

function renderDetailForm(decoration) {
  const detail = detailEl();
  if (!detail || !decoration) {
    detail?.classList.add("hidden");
    return;
  }
  detail.classList.remove("hidden");
  const imageInput = document.getElementById("scene-decoration-image");
  const xInput = document.getElementById("scene-decoration-x");
  const yInput = document.getElementById("scene-decoration-y");
  const widthInput = document.getElementById("scene-decoration-width");
  const heightInput = document.getElementById("scene-decoration-height");
  const bgWidthInput = document.getElementById("scene-decoration-bg-width");
  const bgHeightInput = document.getElementById("scene-decoration-bg-height");
  const repeatInput = document.getElementById("scene-decoration-repeat");
  const spriteFields = document.getElementById("scene-decoration-sprite-fields");
  const backgroundFields = document.getElementById("scene-decoration-background-fields");
  const upBtn = document.getElementById("scene-decoration-up");
  const downBtn = document.getElementById("scene-decoration-down");

  if (imageInput) imageInput.value = decoration.image ?? "";
  if (repeatInput) repeatInput.value = decoration.repeat ?? "repeat";
  const isBackground = decoration.kind === "background";
  if (isBackground) {
    if (bgWidthInput) {
      bgWidthInput.value = decoration.width > 0 ? String(decoration.width) : "";
    }
    if (bgHeightInput) {
      bgHeightInput.value = decoration.height > 0 ? String(decoration.height) : "";
    }
  } else {
    if (xInput) xInput.value = String(decoration.x ?? 0);
    if (yInput) yInput.value = String(decoration.y ?? 0);
    if (widthInput) widthInput.value = String(decoration.width ?? CELL_SIZE);
    if (heightInput) heightInput.value = String(decoration.height ?? CELL_SIZE);
  }

  spriteFields?.classList.toggle("hidden", isBackground);
  backgroundFields?.classList.toggle("hidden", !isBackground);
  upBtn?.toggleAttribute("disabled", isBackground);
  downBtn?.toggleAttribute("disabled", isBackground);
}

function pickDecorationImageFile() {
  const input = document.getElementById("decoration-image-upload-input");
  if (!input) return Promise.resolve(null);
  return new Promise((resolve) => {
    input.value = "";
    const onChange = async () => {
      input.removeEventListener("change", onChange);
      const file = input.files?.[0];
      if (!file) {
        resolve(null);
        return;
      }
      try {
        const result = await uploadDecorationAsset(file);
        resolve(result.path ?? null);
      } catch (err) {
        alert(err.message || String(err));
        resolve(null);
      }
    };
    input.addEventListener("change", onChange);
    input.click();
  });
}

async function browseDecorationImageForDetail() {
  const path = await pickDecorationImageFile();
  if (!path) return;
  const imageInput = document.getElementById("scene-decoration-image");
  if (imageInput) imageInput.value = path;
}

async function addSpriteDecoration() {
  const image = await pickDecorationImageFile();
  if (!image) return;
  const defaultWidth = CELL_SIZE * 2;
  const defaultHeight = CELL_SIZE * 2;
  try {
    const data = await postCreateDecoration({
      kind: "sprite",
      image,
      x: 0,
      y: 0,
      width: defaultWidth,
      height: defaultHeight,
    });
    if (data.decoration?.id) selectedDecorationId = data.decoration.id;
    if (data.snapshot && onStateRefresh) onStateRefresh(data.snapshot);
  } catch (err) {
    alert(err.message || String(err));
  }
}

async function addBackgroundDecoration() {
  const image = await pickDecorationImageFile();
  if (!image) return;
  try {
    const data = await postCreateDecoration({
      kind: "background",
      image,
      repeat: "repeat",
    });
    if (data.decoration?.id) selectedDecorationId = data.decoration.id;
    if (data.snapshot && onStateRefresh) onStateRefresh(data.snapshot);
  } catch (err) {
    alert(err.message || String(err));
  }
}

async function deleteSelectedDecoration() {
  if (!selectedDecorationId) return;
  if (!window.confirm(`Delete decoration ${selectedDecorationId}?`)) return;
  try {
    const data = await deleteDecoration({ decoration_id: selectedDecorationId });
    selectedDecorationId = null;
    if (data.snapshot && onStateRefresh) onStateRefresh(data.snapshot);
  } catch (err) {
    alert(err.message || String(err));
  }
}

async function reorderSelected(direction) {
  if (!selectedDecorationId) return;
  try {
    const data = await reorderDecoration({
      decoration_id: selectedDecorationId,
      direction,
    });
    if (data.snapshot && onStateRefresh) onStateRefresh(data.snapshot);
  } catch (err) {
    alert(err.message || String(err));
  }
}

async function applyDetailForm() {
  if (!selectedDecorationId) return;
  const image = document.getElementById("scene-decoration-image")?.value?.trim();
  const payload = { decoration_id: selectedDecorationId, image };
  const repeat = document.getElementById("scene-decoration-repeat")?.value?.trim();
  if (repeat) payload.repeat = repeat;

  const selected = activeAreaView(getSnapshot()).decorations?.find(
    (d) => d.id === selectedDecorationId,
  );
  if (selected?.kind === "background") {
    payload.width = parseBackgroundTileDim(
      document.getElementById("scene-decoration-bg-width")?.value,
    );
    payload.height = parseBackgroundTileDim(
      document.getElementById("scene-decoration-bg-height")?.value,
    );
  } else {
    const x = Number.parseInt(document.getElementById("scene-decoration-x")?.value ?? "", 10);
    const y = Number.parseInt(document.getElementById("scene-decoration-y")?.value ?? "", 10);
    const width = Number.parseInt(
      document.getElementById("scene-decoration-width")?.value ?? "",
      10,
    );
    const height = Number.parseInt(
      document.getElementById("scene-decoration-height")?.value ?? "",
      10,
    );
    if (!Number.isNaN(x)) payload.x = x;
    if (!Number.isNaN(y)) payload.y = y;
    if (!Number.isNaN(width)) payload.width = width;
    if (!Number.isNaN(height)) payload.height = height;
  }
  try {
    const data = await updateDecoration(payload);
    if (data.snapshot && onStateRefresh) onStateRefresh(data.snapshot);
  } catch (err) {
    alert(err.message || String(err));
  }
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function escapeAttr(text) {
  return String(text).replace(/"/g, "&quot;");
}
