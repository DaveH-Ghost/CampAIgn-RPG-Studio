/** Settings modal: in-memory LLM config + custom memory module upload (V0.4.6). */

import {
  getLlmSettings,
  getMemoryModules,
  putLlmSettings,
  uploadMemoryModule,
} from "./api.js";

export function initSettings({ showToastFn }) {
  const backdrop = document.getElementById("settings-backdrop");
  const openBtn = document.getElementById("open-settings");
  const closeBtn = document.getElementById("settings-close");
  const apiKeyInput = document.getElementById("settings-api-key");
  const keyStatus = document.getElementById("settings-key-status");
  const modelInput = document.getElementById("settings-model");
  const llmSaveBtn = document.getElementById("settings-llm-save");
  const moduleFileInput = document.getElementById("settings-module-upload");
  const moduleUploadBtn = document.getElementById("settings-module-upload-btn");
  const customList = document.getElementById("settings-custom-modules");
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

  async function refreshCustomModuleList() {
    if (!customList) return;
    try {
      const catalog = await getMemoryModules();
      const customs = catalog.custom_modules || [];
      customList.innerHTML = "";
      if (customs.length === 0) {
        const item = document.createElement("li");
        item.textContent = "No custom modules loaded.";
        customList.appendChild(item);
        return;
      }
      for (const mod of customs) {
        const item = document.createElement("li");
        item.textContent = mod.filename
          ? `${mod.label || mod.id} (${mod.id}) — ${mod.filename}`
          : `${mod.label || mod.id} (${mod.id})`;
        customList.appendChild(item);
      }
    } catch (err) {
      const item = document.createElement("li");
      item.textContent = String(err.message || err);
      customList.appendChild(item);
    }
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
      await refreshCustomModuleList();
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

  moduleUploadBtn?.addEventListener("click", async () => {
    setError("");
    const file = moduleFileInput?.files?.[0];
    if (!file) {
      setError("Choose a .py file first.");
      return;
    }
    try {
      const result = await uploadMemoryModule(file);
      if (moduleFileInput) moduleFileInput.value = "";
      await refreshCustomModuleList();
      showToastFn(result.message || `Loaded ${result.module_id}`);
    } catch (err) {
      setError(String(err.message || err));
    }
  });

  return { refreshCustomModuleList };
}
