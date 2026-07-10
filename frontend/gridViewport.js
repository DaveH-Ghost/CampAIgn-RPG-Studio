/**
 * Grid viewport — black canvas, pannable world (V0.3.2c1).
 * Middle mouse button drag to pan; pan offset preserved across re-renders.
 */

export const CELL_SIZE = 64;

let panX = 0;
let panY = 0;
let isPanning = false;
let pointerStartX = 0;
let pointerStartY = 0;
let panAtStartX = 0;
let panAtStartY = 0;
let centered = false;

let viewportEl = null;
let worldEl = null;

function applyPan() {
  if (!worldEl) return;
  worldEl.style.transform = `translate(${panX}px, ${panY}px)`;
}

function onMouseDown(e) {
  if (e.button !== 1 || !viewportEl) return;
  e.preventDefault();
  isPanning = true;
  pointerStartX = e.clientX;
  pointerStartY = e.clientY;
  panAtStartX = panX;
  panAtStartY = panY;
  viewportEl.classList.add("is-panning");
}

function onMouseMove(e) {
  if (!isPanning) return;
  panX = panAtStartX + (e.clientX - pointerStartX);
  panY = panAtStartY + (e.clientY - pointerStartY);
  applyPan();
}

function onMouseUp(e) {
  if (!isPanning) return;
  if (e.button !== 0 && e.button !== 1 && e.button !== 2) return;
  isPanning = false;
  viewportEl?.classList.remove("is-panning");
}

export function initGridViewport(viewport, world) {
  viewportEl = viewport;
  worldEl = world;

  viewport.addEventListener("mousedown", onMouseDown);
  viewport.addEventListener("auxclick", (e) => {
    if (e.button === 1) e.preventDefault();
  });
  document.addEventListener("mousemove", onMouseMove);
  document.addEventListener("mouseup", onMouseUp);
}

/** Center the grid in the viewport once, after first successful render. */
export function maybeCenterGrid(gridEl) {
  if (centered || !viewportEl || !gridEl) return;
  const gw = gridEl.offsetWidth;
  const gh = gridEl.offsetHeight;
  if (!gw || !gh) return;

  panX = (viewportEl.clientWidth - gw) / 2;
  panY = (viewportEl.clientHeight - gh) / 2;
  centered = true;
  applyPan();
}
