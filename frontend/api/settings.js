/** HTTP helpers for health, LLM, and hosting settings endpoints. */

export async function getHealth() {
  const res = await fetch("/api/health");
  if (!res.ok) {
    throw new Error(`GET /api/health failed: HTTP ${res.status}`);
  }
  return res.json();
}

export async function getLlmSettings() {
  const res = await fetch("/api/settings/llm");
  if (!res.ok) {
    throw new Error(`GET /api/settings/llm failed: HTTP ${res.status}`);
  }
  return res.json();
}

export async function putLlmSettings({
  provider,
  api_key,
  model,
  max_input_tokens,
  input_warning_percent,
  concurrent_llm_calls,
}) {
  const body = {};
  if (provider !== undefined) body.provider = provider;
  if (api_key !== undefined) body.api_key = api_key;
  if (model !== undefined) body.model = model;
  if (max_input_tokens !== undefined) body.max_input_tokens = max_input_tokens;
  if (input_warning_percent !== undefined) {
    body.input_warning_percent = input_warning_percent;
  }
  if (concurrent_llm_calls !== undefined) {
    body.concurrent_llm_calls = concurrent_llm_calls;
  }
  const res = await fetch("/api/settings/llm", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || `HTTP ${res.status}`);
  }
  return data;
}

export async function getHostingSettings() {
  const res = await fetch("/api/settings/hosting");
  if (!res.ok) {
    throw new Error(`GET /api/settings/hosting failed: HTTP ${res.status}`);
  }
  return res.json();
}

export async function putHostingSettings({ public_base_url }) {
  const res = await fetch("/api/settings/hosting", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ public_base_url }),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || `HTTP ${res.status}`);
  }
  return data;
}
