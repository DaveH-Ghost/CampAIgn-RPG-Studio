/** Settings modal: in-memory LLM config. */

import { getLlmSettings, putLlmSettings } from "./api.js";

export function initSettings({ showToastFn }) {
  const backdrop = document.getElementById("settings-backdrop");
  const openBtn = document.getElementById("open-settings");
  const closeBtn = document.getElementById("settings-close");
  const apiKeyInput = document.getElementById("settings-api-key");
  const keyStatus = document.getElementById("settings-key-status");
  const modelInput = document.getElementById("settings-model");
  const llmSaveBtn = document.getElementById("settings-llm-save");
  const errorEl = document.getElementById("settings-error");

  if (!backdrop || !openBtn) return;

  function setError(message) {
    if (errorEl) errorEl.textContent = message || "";
  }

  function closeSettings() {
    backdrop.classList.add("hidden");
    setError("");
    if (apiKeyInput) apiKeyInput.value = "";
  }

  async function openSettings() {
    setError("");
    try {
      const data = await getLlmSettings();
      if (modelInput) modelInput.value = data.model || "";
      if (keyStatus) {
        keyStatus.textContent = data.key_configured
          ? "API key configured (*****)."
          : "No API key set in this session.";
      }
      if (apiKeyInput) apiKeyInput.value = "";
      backdrop.classList.remove("hidden");
    } catch (err) {
      showToastFn(String(err.message || err), true);
    }
  }

  openBtn.addEventListener("click", () => {
    void openSettings();
  });

  closeBtn?.addEventListener("click", closeSettings);
  backdrop.addEventListener("click", (e) => {
    if (e.target === backdrop) closeSettings();
  });

  llmSaveBtn?.addEventListener("click", async () => {
    setError("");
    try {
      const payload = {
        model: modelInput?.value?.trim() || "",
      };
      const key = apiKeyInput?.value?.trim();
      if (key) payload.api_key = key;
      const data = await putLlmSettings(payload);
      if (modelInput) modelInput.value = data.model || "";
      if (keyStatus) {
        keyStatus.textContent = data.key_configured
          ? "API key configured (*****)."
          : "No API key set in this session.";
      }
      if (apiKeyInput) apiKeyInput.value = "";
      showToastFn("LLM settings applied (this session only).");
    } catch (err) {
      setError(String(err.message || err));
    }
  });

  return {};
}
