/** Settings modal: in-memory LLM config (provider, key, model, token budget). */

import { getLlmSettings, putLlmSettings } from "./api.js";

/** DeepSeek V4 Flash — different catalog ids per provider. */
const DEEPSEEK_V4_FLASH = {
  openrouter: "deepseek/deepseek-v4-flash",
  featherless: "deepseek-ai/DeepSeek-V4-Flash",
};

function normalizeModelId(value) {
  return String(value || "")
    .trim()
    .toLowerCase();
}

function mapDeepSeekV4FlashModel(currentModel, nextProvider) {
  const current = normalizeModelId(currentModel);
  const openrouterId = normalizeModelId(DEEPSEEK_V4_FLASH.openrouter);
  const featherlessId = normalizeModelId(DEEPSEEK_V4_FLASH.featherless);
  if (current !== openrouterId && current !== featherlessId) {
    return null;
  }
  return DEEPSEEK_V4_FLASH[nextProvider] || null;
}

export function initSettings({ showToastFn, onSettingsAppliedFn }) {
  const backdrop = document.getElementById("settings-backdrop");
  const openBtn = document.getElementById("open-settings");
  const closeBtn = document.getElementById("settings-close");
  const providerSelect = document.getElementById("settings-provider");
  const apiKeyInput = document.getElementById("settings-api-key");
  const apiKeyLabel = document.getElementById("settings-api-key-label");
  const keyStatus = document.getElementById("settings-key-status");
  const modelInput = document.getElementById("settings-model");
  const maxTokensInput = document.getElementById("settings-max-input-tokens");
  const warningPercentInput = document.getElementById("settings-input-warning-percent");
  const llmSaveBtn = document.getElementById("settings-llm-save");
  const errorEl = document.getElementById("settings-error");

  let settingsDefaults = null;

  if (!backdrop || !openBtn) return;

  function setError(message) {
    if (errorEl) errorEl.textContent = message || "";
  }

  function syncProviderHints(provider, defaults) {
    const isFeatherless = provider === "featherless";
    if (apiKeyLabel) {
      apiKeyLabel.textContent = isFeatherless ? "Featherless API key" : "OpenRouter API key";
    }
    if (apiKeyInput) {
      apiKeyInput.placeholder = isFeatherless ? "featherless key" : "sk-or-...";
    }
    if (modelInput) {
      const d = defaults || settingsDefaults;
      modelInput.placeholder = isFeatherless
        ? d?.featherless_model || DEEPSEEK_V4_FLASH.featherless
        : d?.openrouter_model || DEEPSEEK_V4_FLASH.openrouter;
    }
  }

  function applySettingsToForm(data) {
    settingsDefaults = data.defaults || settingsDefaults;
    if (providerSelect) providerSelect.value = data.provider || "openrouter";
    if (modelInput) modelInput.value = data.model || "";
    if (maxTokensInput) {
      maxTokensInput.value = String(
        data.max_input_tokens ?? data.defaults?.max_input_tokens ?? 32768,
      );
    }
    if (warningPercentInput) {
      warningPercentInput.value = String(
        data.input_warning_percent ?? data.defaults?.input_warning_percent ?? 90,
      );
    }
    if (keyStatus) {
      keyStatus.textContent = data.key_configured
        ? "API key configured (*****)."
        : "No API key set in this session.";
    }
    syncProviderHints(data.provider || "openrouter", data.defaults);
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
      applySettingsToForm(data);
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

  providerSelect?.addEventListener("change", () => {
    const nextProvider = providerSelect.value;
    const mapped = mapDeepSeekV4FlashModel(modelInput?.value, nextProvider);
    if (mapped && modelInput) {
      modelInput.value = mapped;
    }
    syncProviderHints(nextProvider, settingsDefaults);
  });

  llmSaveBtn?.addEventListener("click", async () => {
    setError("");
    try {
      const payload = {
        provider: providerSelect?.value || "openrouter",
        model: modelInput?.value?.trim() || "",
        max_input_tokens: Number(maxTokensInput?.value || 32768),
        input_warning_percent: Number(warningPercentInput?.value || 90),
      };
      const key = apiKeyInput?.value?.trim();
      if (key) payload.api_key = key;
      const data = await putLlmSettings(payload);
      if (data.ok === false) {
        setError(data.message || "Failed to apply settings.");
        return;
      }
      applySettingsToForm(data);
      if (apiKeyInput) apiKeyInput.value = "";
      showToastFn("LLM settings applied (this session only).");
      if (typeof onSettingsAppliedFn === "function") {
        await onSettingsAppliedFn(data);
      }
    } catch (err) {
      setError(String(err.message || err));
    }
  });

  return {};
}
