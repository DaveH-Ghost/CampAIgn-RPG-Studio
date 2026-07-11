/**
 * Session coordinate mode (full vs relative/D&D-style prompts).
 */

import { putCoordinateMode } from "./api.js";

let modeSelect;
let showToast = () => {};
let onUpdatedFn = async () => {};

export function initCoordinateMode({ modeSelectEl, showToastFn, onUpdatedFn: onUpdated }) {
  modeSelect = modeSelectEl;
  showToast = showToastFn;
  onUpdatedFn = onUpdated ?? onUpdatedFn;

  modeSelect.addEventListener("change", () => {
    saveCoordinateMode();
  });
}

export function syncCoordinateModeFromSnapshot(snapshot) {
  if (!modeSelect || !snapshot) return;
  if (document.activeElement === modeSelect) return;
  const mode = snapshot.coordinate_mode ?? "full";
  modeSelect.value = mode === "relative" ? "relative" : "full";
}

async function saveCoordinateMode() {
  const mode = modeSelect.value === "relative" ? "relative" : "full";
  try {
    const data = await putCoordinateMode(mode);
    if (!data.ok) {
      showToast(data.message || "Failed to update coordinate mode.", true);
      return;
    }
    showToast(
      mode === "relative"
        ? "Relative mode — bearings and entity-id moves (D&D-friendly)."
        : "Full coordinate mode.",
      false,
    );
    await onUpdatedFn(data.snapshot ?? null);
  } catch (err) {
    showToast(err.message || String(err), true);
  }
}
