/**
 * Session vision unit fields (V0.4.1c) — sidebar inputs for passive vision config.
 */

import { putVisionUnits } from "./api.js";

let showToast = () => {};
let onUpdatedFn = async () => {};

let unitsInput;
let unitsPerTileInput;
let saveTimer = null;
let saveInFlight = false;

export function initVisionUnits({
  unitsInputEl,
  unitsPerTileInputEl,
  showToastFn,
  onUpdatedFn: onUpdated,
}) {
  unitsInput = unitsInputEl;
  unitsPerTileInput = unitsPerTileInputEl;
  showToast = showToastFn;
  onUpdatedFn = onUpdated ?? onUpdatedFn;

  unitsInput.addEventListener("input", () => {
    unitsInput.value = unitsInput.value.replace(/[^A-Za-z]/g, "");
    scheduleSave();
  });
  unitsPerTileInput.addEventListener("input", () => {
    unitsPerTileInput.value = unitsPerTileInput.value.replace(/[^0-9]/g, "");
    scheduleSave();
  });
  unitsInput.addEventListener("blur", () => flushSave());
  unitsPerTileInput.addEventListener("blur", () => flushSave());
}

export function syncVisionUnitsFromSnapshot(snapshot) {
  if (!unitsInput || !unitsPerTileInput || !snapshot) return;
  const snap = snapshot;
  if (document.activeElement !== unitsInput) {
    unitsInput.value = snap.vision_units ?? "";
  }
  if (document.activeElement !== unitsPerTileInput) {
    const perTile = snap.vision_units_per_tile;
    unitsPerTileInput.value =
      perTile == null || perTile === "" ? "" : String(perTile);
  }
}

function readPayload() {
  const units = unitsInput.value.trim();
  const perTileRaw = unitsPerTileInput.value.trim();
  const unitsPerTile = perTileRaw === "" ? null : Number(perTileRaw);
  return { units, units_per_tile: unitsPerTile };
}

function scheduleSave() {
  if (saveTimer) window.clearTimeout(saveTimer);
  saveTimer = window.setTimeout(() => {
    saveTimer = null;
    saveVisionUnits();
  }, 400);
}

function flushSave() {
  if (saveTimer) {
    window.clearTimeout(saveTimer);
    saveTimer = null;
  }
  return saveVisionUnits();
}

async function saveVisionUnits() {
  if (saveInFlight) return;
  const payload = readPayload();
  if (payload.units_per_tile != null && payload.units_per_tile <= 0) {
    showToast("Units per tile must be a positive number.", true);
    return;
  }
  saveInFlight = true;
  try {
    const result = await putVisionUnits(payload);
    if (!result.ok) throw new Error(result.message);
    if (document.activeElement !== unitsInput) {
      unitsInput.value = result.vision_units ?? "";
    }
    if (document.activeElement !== unitsPerTileInput) {
      const perTile = result.vision_units_per_tile;
      unitsPerTileInput.value =
        perTile == null || perTile === "" ? "" : String(perTile);
    }
    if (result.snapshot) {
      await onUpdatedFn(result.snapshot);
    }
  } catch (err) {
    showToast(String(err.message || err), true);
  } finally {
    saveInFlight = false;
  }
}
