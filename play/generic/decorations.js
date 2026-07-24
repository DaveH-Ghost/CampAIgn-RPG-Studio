/**
 * Read-only scene decoration render for /play/generic (no GM edit UI).
 */

import { resolveAppearanceUrl } from "/static/appearance.js?v=1.7.4f";
import { CELL_SIZE } from "/static/gridViewport.js?v=1.7.4f";

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function sortedDecorations(decorations) {
  return [...asArray(decorations)].sort(
    (a, b) => (a.z_index ?? 0) - (b.z_index ?? 0) || String(a.id).localeCompare(String(b.id)),
  );
}

function backgroundSizeCss(width, height) {
  const w = Number(width) > 0 ? `${width}px` : "auto";
  const h = Number(height) > 0 ? `${height}px` : "auto";
  return `${w} ${h}`;
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
  const url = resolveAppearanceUrl(decoration.image);
  el.style.left = `${decoration.x ?? 0}px`;
  el.style.top = `${decoration.y ?? 0}px`;
  el.style.width = `${decoration.width ?? CELL_SIZE}px`;
  el.style.height = `${decoration.height ?? CELL_SIZE}px`;
  el.style.zIndex = String(decoration.z_index ?? 0);
  el.style.pointerEvents = "none";
  if (url) {
    const img = document.createElement("img");
    img.src = url;
    img.alt = "";
    img.draggable = false;
    el.appendChild(img);
  }
  return el;
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
}
