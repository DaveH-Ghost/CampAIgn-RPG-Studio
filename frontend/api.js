/** HTTP helpers for campaign-rpg-studio API. */

export async function getHealth() {
  const res = await fetch("/api/health");
  if (!res.ok) {
    throw new Error(`GET /api/health failed: HTTP ${res.status}`);
  }
  return res.json();
}

export async function getState() {
  const res = await fetch("/api/state");
  if (!res.ok) {
    throw new Error(`GET /api/state failed: HTTP ${res.status}`);
  }
  return res.json();
}

export async function fetchInteractionHandlers() {
  const res = await fetch("/api/interaction-handlers");
  if (!res.ok) {
    throw new Error(`GET /api/interaction-handlers failed: HTTP ${res.status}`);
  }
  return res.json();
}

export async function postCommand(line) {
  const res = await fetch("/api/command", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ line }),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.message || `HTTP ${res.status}`);
  }
  return data;
}

export async function postActiveAgent(nameOrId) {
  const res = await fetch("/api/active-agent", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name_or_id: nameOrId }),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.message || `HTTP ${res.status}`);
  }
  return data;
}

export async function postActiveArea(areaId) {
  const res = await fetch("/api/active-area", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ area_id: areaId }),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.message || `HTTP ${res.status}`);
  }
  return data;
}

export async function postCreateArea({ areaId, description, width, height }) {
  const res = await fetch("/api/create-area", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      area_id: areaId,
      description: description ?? "",
      width: Number(width),
      height: Number(height),
    }),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.message || `HTTP ${res.status}`);
  }
  return data;
}

export async function postEditArea({ areaId, description, width, height }) {
  const res = await fetch("/api/edit-area", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      area_id: areaId,
      description,
      width: width !== "" && width !== undefined ? Number(width) : undefined,
      height: height !== "" && height !== undefined ? Number(height) : undefined,
    }),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.message || `HTTP ${res.status}`);
  }
  return data;
}

export async function postDeleteArea(areaId) {
  const res = await fetch("/api/delete-area", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ area_id: areaId }),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.message || `HTTP ${res.status}`);
  }
  return data;
}

export async function postTurn({ agentId, includeExamples } = {}) {
  const body = {};
  if (agentId) body.agent_id = agentId;
  if (includeExamples !== undefined) body.include_examples = includeExamples;

  const res = await fetch("/api/turn", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.message || `HTTP ${res.status}`);
  }
  return data;
}

export async function postManualTurn({ agentId, compoundTurn } = {}) {
  const body = { compound_turn: compoundTurn };
  if (agentId) body.agent_id = agentId;

  const res = await fetch("/api/turn/manual", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.message || `HTTP ${res.status}`);
  }
  return data;
}

export async function postEvent(text, agentIds = null) {
  const body = { text };
  if (Array.isArray(agentIds) && agentIds.length > 0) {
    body.agent_ids = agentIds;
  }

  const res = await fetch("/api/event", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.message || `HTTP ${res.status}`);
  }
  return data;
}

export async function getPrompt(agentId) {
  const params = agentId ? `?agent_id=${encodeURIComponent(agentId)}` : "";
  const res = await fetch(`/api/prompt${params}`);
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.message || `HTTP ${res.status}`);
  }
  return data;
}

export async function getPromptBlocks(agentId) {
  const params = agentId ? `?agent_id=${encodeURIComponent(agentId)}` : "";
  const res = await fetch(`/api/prompt-blocks${params}`);
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.message || `HTTP ${res.status}`);
  }
  return data;
}

export async function putPromptBlocks(blocks) {
  const res = await fetch("/api/prompt-blocks", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ blocks }),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.message || `HTTP ${res.status}`);
  }
  return data;
}

export async function resetPromptBlocks() {
  const res = await fetch("/api/prompt-blocks/reset", { method: "POST" });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.message || `HTTP ${res.status}`);
  }
  return data;
}

export async function getPromptSlots(agentId) {
  const params = agentId ? `?agent_id=${encodeURIComponent(agentId)}` : "";
  const res = await fetch(`/api/prompt-slots${params}`);
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.message || `HTTP ${res.status}`);
  }
  return data;
}

export async function getPromptBlockCatalog() {
  const res = await fetch("/api/prompt-block-catalog");
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.message || `HTTP ${res.status}`);
  }
  return data;
}

export async function fetchTurnVerbs() {
  const res = await fetch("/api/turn-verbs");
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.message || `HTTP ${res.status}`);
  }
  return data;
}

export async function putVisionUnits({ units, units_per_tile }) {
  const res = await fetch("/api/vision-units", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ units, units_per_tile }),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.message || `HTTP ${res.status}`);
  }
  return data;
}

export async function putCoordinateMode(mode) {
  const res = await fetch("/api/coordinate-mode", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode }),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.message || `HTTP ${res.status}`);
  }
  return data;
}

export async function previewPromptBlocks(blocks, agentId) {
  const body = { blocks };
  if (agentId) body.agent_id = agentId;
  const res = await fetch("/api/prompt-blocks/preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.message || `HTTP ${res.status}`);
  }
  return data;
}

/** CLI-safe double-quoted string (v1: strip embedded quotes). */
export function cliQuote(value) {
  const text = String(value ?? "").replace(/"/g, "'");
  return `"${text}"`;
}

export function buildCreateObject({
  name,
  pdesc,
  desc,
  appearance,
  x,
  y,
  width = 1,
  height = 1,
  blocksMovement = true,
  movementExceptions = "",
  hidden = false,
}) {
  let line =
    `create-object name ${cliQuote(name)} pdesc ${cliQuote(pdesc)} ` +
    `desc ${cliQuote(desc)} at ${x},${y}`;
  const footprintWidth = Number(width) || 1;
  const footprintHeight = Number(height) || 1;
  if (footprintWidth !== 1 || footprintHeight !== 1) {
    line += ` width ${footprintWidth} height ${footprintHeight}`;
  }
  if (appearance) {
    line += ` appearance ${cliQuote(appearance)}`;
  }
  if (blocksMovement === false) {
    line += " blocks-movement false";
  }
  if (hidden) {
    line += " hidden true";
  }
  const exceptions = String(movementExceptions ?? "").trim();
  if (blocksMovement !== false && exceptions) {
    line += ` movement-exception ${cliQuote(exceptions)}`;
  }
  return line;
}

/** Extract object id from a successful create-object CLI response. */
export function parseCreatedObjectId(message) {
  const match = /^Created object (obj_\S+)/.exec(String(message ?? "").trim());
  return match ? match[1] : null;
}

/** Extract agent id from a successful create-agent CLI response. */
export function parseCreatedAgentId(message) {
  const match = /^Created agent (agent_\S+)/.exec(String(message ?? "").trim());
  return match ? match[1] : null;
}

export async function postEntityPrivateData(entityId, privateData) {
  const res = await fetch("/api/entity-private-data", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      entity_id: entityId,
      private_data: privateData ?? "",
    }),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.message || `PUT /api/entity-private-data failed: HTTP ${res.status}`);
  }
  return data;
}

export async function getMemoryModules() {
  const res = await fetch("/api/memory-modules");
  const data = await res.json();
  if (!res.ok || !data.ok) {
    throw new Error(data.message || `GET /api/memory-modules failed: HTTP ${res.status}`);
  }
  return data;
}

const MEMORY_OPTION_FLAGS = {
  memoryWindow: "memory-window",
  memoryBudget: "memory-budget",
  memorySummaryInterval: "memory-summary-interval",
  memorySummaryMax: "memory-summary-max",
  memorySummaryTail: "memory-summary-tail",
};

function hasMemoryCliOptions(memoryOptions) {
  return Object.values(memoryOptions).some(
    (value) => value !== undefined && value !== null && String(value).trim() !== "",
  );
}

export function memoryOptionFieldName(flag) {
  const entry = Object.entries(MEMORY_OPTION_FLAGS).find(([, cliFlag]) => cliFlag === flag);
  return entry ? entry[0] : flag.replace(/-([a-z])/g, (_, c) => c.toUpperCase());
}

export function buildCreateAgent({
  name,
  pdesc,
  desc,
  personality,
  appearance,
  moveSpeed,
  memoryModule,
  memoryOptions = {},
  isPlayer,
  blocksMovement = true,
  movementExceptions = "",
  x,
  y,
}) {
  let line =
    `create-agent name ${cliQuote(name)} pdesc ${cliQuote(pdesc)} ` +
    `desc ${cliQuote(desc)} personality ${cliQuote(personality)} at ${x},${y}`;
  if (appearance) {
    line += ` appearance ${cliQuote(appearance)}`;
  }
  if (moveSpeed) {
    line += ` move-speed ${moveSpeed}`;
  }
  if (isPlayer) {
    line += " player true";
  }
  if (blocksMovement === false) {
    line += " blocks-movement false";
  } else {
    line += " blocks-movement true";
  }
  const exceptions = String(movementExceptions ?? "").trim();
  if (exceptions) {
    line += ` movement-exception ${cliQuote(exceptions)}`;
  }
  const moduleId = String(memoryModule ?? "").trim() || "recent_turns";
  if (moduleId !== "recent_turns") {
    line += ` memory ${moduleId}`;
  } else if (hasMemoryCliOptions(memoryOptions)) {
    line += " memory recent_turns";
  }
  for (const [field, flag] of Object.entries(MEMORY_OPTION_FLAGS)) {
    const value = memoryOptions[field];
    if (value !== undefined && value !== null && String(value).trim() !== "") {
      line += ` ${flag} ${String(value).trim()}`;
    }
  }
  return line;
}

export function buildCompoundTurnPayload(data) {
  const action = data.action || "none";
  const payload = {
    reasoning: data.reasoning,
    action,
  };
  if (data.move?.trim()) payload.move = data.move.trim();
  if (data.look?.trim()) payload.look = data.look.trim();
  if (data.say?.trim()) payload.say = data.say.trim();
  if (action === "interact" || action === "emote") {
    payload.target = data.target.trim();
    payload.verb = data.verb.trim();
  }
  if (action === "verb") {
    payload.verb = String(data.turn_verb ?? data.verb ?? "").trim();
    if (data.target?.trim()) payload.target = data.target.trim();
  }
  return payload;
}

export function buildEditObject({
  id,
  name,
  pdesc,
  desc,
  appearance,
  areaId,
  sourceAreaId,
  x,
  y,
  width,
  height,
  blocksMovement,
  movementExceptions,
  hidden,
}) {
  const parts = [`edit-object ${id}`];
  if (name) parts.push(`name ${cliQuote(name)}`);
  if (pdesc) parts.push(`pdesc ${cliQuote(pdesc)}`);
  if (desc) parts.push(`desc ${cliQuote(desc)}`);
  if (appearance !== undefined) parts.push(`appearance ${cliQuote(appearance)}`);
  if (blocksMovement !== undefined) {
    parts.push(`blocks-movement ${blocksMovement ? "true" : "false"}`);
  }
  if (blocksMovement !== undefined) {
    const exceptions = String(movementExceptions ?? "").trim();
    parts.push(`movement-exception ${cliQuote(exceptions)}`);
  }
  if (hidden !== undefined) {
    parts.push(`hidden ${hidden ? "true" : "false"}`);
  }
  const targetArea = String(areaId ?? "").trim();
  const originArea = String(sourceAreaId ?? "").trim();
  if (targetArea && originArea && targetArea !== originArea) {
    parts.push(`area ${targetArea}`);
  }
  parts.push(`pos ${x},${y}`);
  if (width !== undefined && width !== "") {
    parts.push(`width ${Number(width) || 1}`);
  }
  if (height !== undefined && height !== "") {
    parts.push(`height ${Number(height) || 1}`);
  }
  return parts.join(" ");
}

export function buildEditAgent({
  id,
  name,
  pdesc,
  desc,
  personality,
  appearance,
  moveSpeed,
  isPlayer,
  blocksMovement,
  movementExceptions,
  areaId,
  sourceAreaId,
  x,
  y,
}) {
  const parts = [`edit-agent ${id}`];
  if (name) parts.push(`name ${cliQuote(name)}`);
  if (pdesc) parts.push(`pdesc ${cliQuote(pdesc)}`);
  if (desc) parts.push(`desc ${cliQuote(desc)}`);
  if (personality) parts.push(`personality ${cliQuote(personality)}`);
  if (appearance !== undefined) parts.push(`appearance ${cliQuote(appearance)}`);
  if (moveSpeed !== undefined) {
    if (moveSpeed === "") {
      parts.push('move-speed ""');
    } else {
      parts.push(`move-speed ${moveSpeed}`);
    }
  }
  if (isPlayer !== undefined) {
    parts.push(`player ${isPlayer ? "true" : "false"}`);
  }
  if (blocksMovement !== undefined) {
    parts.push(`blocks-movement ${blocksMovement ? "true" : "false"}`);
  }
  if (blocksMovement !== undefined) {
    const exceptions = String(movementExceptions ?? "").trim();
    parts.push(`movement-exception ${cliQuote(exceptions)}`);
  }
  const targetArea = String(areaId ?? "").trim();
  const originArea = String(sourceAreaId ?? "").trim();
  if (targetArea && originArea && targetArea !== originArea) {
    parts.push(`area ${targetArea}`);
  }
  parts.push(`pos ${x},${y}`);
  return parts.join(" ");
}

export function buildCreateArea({ id, desc, width, height }) {
  let line = `create-area id ${id}`;
  if (desc) line += ` desc ${cliQuote(desc)}`;
  line += ` width ${width} height ${height}`;
  return line;
}

export function buildEditArea({ id, desc, width, height }) {
  const parts = [`edit-area ${id}`];
  if (desc !== undefined && desc !== "") parts.push(`desc ${cliQuote(desc)}`);
  if (width) parts.push(`width ${width}`);
  if (height) parts.push(`height ${height}`);
  return parts.join(" ");
}

export function buildDeleteArea(id) {
  return `delete-area ${id}`;
}

export function buildAddObjectAction(objectId, {
  name,
  range,
  result,
  passive,
  effect,
  handler,
  destArea,
  destX,
  destY,
  kind = "interact",
  haltMovement,
  deleteAfterTrigger,
  triggerExceptions,
}) {
  const parts = [`edit-object ${objectId} add-action ${name} range ${range}`];
  if (kind && kind !== "interact") {
    parts.push(`kind ${kind}`);
  }
  if (kind === "trigger") {
    if (haltMovement !== undefined) {
      parts.push(`halt-movement ${haltMovement ? "true" : "false"}`);
    }
    if (deleteAfterTrigger !== undefined) {
      parts.push(`delete-after-trigger ${deleteAfterTrigger ? "true" : "false"}`);
    }
    const exceptions = String(triggerExceptions ?? "").trim();
    if (exceptions) {
      parts.push(`trigger-exception ${cliQuote(exceptions)}`);
    }
  }
  const selectedHandler = handler || effect;
  if (selectedHandler && selectedHandler !== "none") {
    parts.push(`handler ${selectedHandler}`);
    if (selectedHandler === "move_area") {
      parts.push(`dest-area ${destArea}`, `dest-at ${destX},${destY}`);
    }
  }
  parts.push(`result ${cliQuote(result)}`, `passive ${cliQuote(passive)}`);
  return parts.join(" ");
}

/** CLI lines to create a hidden object plus a trigger action. */
export function buildCreateHiddenTrigger({
  name,
  x,
  y,
  width = 1,
  height = 1,
  areaEvent,
  actionName = "trip",
  range = 0,
  haltMovement = true,
  deleteAfterTrigger = true,
  triggerExceptions = "",
}) {
  const createLine = buildCreateObject({
    name,
    pdesc: "Hidden trigger.",
    desc: "A hidden floor trigger for testing.",
    x,
    y,
    width,
    height,
    blocksMovement: false,
    hidden: true,
  });
  const actionLine = buildAddObjectAction("__OBJECT_ID__", {
    name: actionName,
    range,
    result: "(trigger)",
    passive: areaEvent,
    kind: "trigger",
    haltMovement,
    deleteAfterTrigger,
    triggerExceptions,
    effect: "none",
  });
  return { createLine, actionLine };
}

export function buildRemoveObjectAction(objectId, actionName) {
  return `edit-object ${objectId} remove-action ${actionName}`;
}

function parseContentDispositionFilename(header) {
  if (!header) return "realm-session.json";
  const match = /filename="([^"]+)"/.exec(header);
  return match ? match[1] : "realm-session.json";
}

export async function exportSession() {
  const res = await fetch("/api/session/export");
  if (!res.ok) {
    throw new Error(`GET /api/session/export failed: HTTP ${res.status}`);
  }
  const blob = await res.blob();
  const filename = parseContentDispositionFilename(
    res.headers.get("Content-Disposition"),
  );
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
  return { filename };
}

export async function importSession(snapshot) {
  const res = await fetch("/api/session/import", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(snapshot),
  });
  const data = await res.json();
  if (!res.ok) {
    const detail = data.detail || data.message || `HTTP ${res.status}`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

export async function getLlmSettings() {
  const res = await fetch("/api/settings/llm");
  if (!res.ok) {
    throw new Error(`GET /api/settings/llm failed: HTTP ${res.status}`);
  }
  return res.json();
}

export async function putLlmSettings({ api_key, model }) {
  const body = {};
  if (api_key !== undefined) body.api_key = api_key;
  if (model !== undefined) body.model = model;
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

export async function uploadMemoryModule(file) {
  const form = new FormData();
  form.append("file", file, file.name);
  const res = await fetch("/api/memory-modules/upload", {
    method: "POST",
    body: form,
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || `HTTP ${res.status}`);
  }
  return data;
}

export async function fetchPlugins() {
  const res = await fetch("/api/plugins");
  const data = await res.json();
  if (!res.ok || !data.ok) {
    throw new Error(data.message || `GET /api/plugins failed: HTTP ${res.status}`);
  }
  return data;
}

export async function enablePlugin(pluginId) {
  const res = await fetch(`/api/plugins/${encodeURIComponent(pluginId)}/enable`, {
    method: "POST",
  });
  const data = await res.json();
  if (!res.ok || !data.ok) {
    throw new Error(data.detail || data.message || `HTTP ${res.status}`);
  }
  return data;
}

export async function disablePlugin(pluginId) {
  const res = await fetch(`/api/plugins/${encodeURIComponent(pluginId)}/disable`, {
    method: "POST",
  });
  const data = await res.json();
  if (!res.ok || !data.ok) {
    throw new Error(data.detail || data.message || `HTTP ${res.status}`);
  }
  return data;
}

export async function fetchPluginPanel(pluginId) {
  const res = await fetch(`/api/plugins/${encodeURIComponent(pluginId)}/panel`);
  const data = await res.json();
  if (!res.ok || !data.ok) {
    throw new Error(data.detail || data.message || `HTTP ${res.status}`);
  }
  return data;
}

export async function postPluginAction(pluginId, actionId, params = {}) {
  const res = await fetch(`/api/plugins/${encodeURIComponent(pluginId)}/action`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action_id: actionId, params }),
  });
  const data = await res.json();
  if (!res.ok || !data.ok) {
    throw new Error(data.detail || data.message || `HTTP ${res.status}`);
  }
  return data;
}

export async function fetchEntityTemplates() {
  const res = await fetch("/api/entity-templates");
  const data = await res.json();
  if (!res.ok || !data.ok) {
    throw new Error(data.message || `GET /api/entity-templates failed: HTTP ${res.status}`);
  }
  return data;
}

export async function postSaveEntityTemplate({
  kind,
  entityId,
  filename,
  includeMemory = false,
}) {
  const res = await fetch("/api/entity-templates/save-from-entity", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      kind,
      entity_id: entityId,
      filename,
      include_memory: includeMemory,
    }),
  });
  const data = await res.json();
  if (!res.ok || !data.ok) {
    throw new Error(data.detail || data.message || `HTTP ${res.status}`);
  }
  return data;
}

async function downloadAttachmentResponse(res, fallbackFilename) {
  if (!res.ok) {
    let message = `HTTP ${res.status}`;
    try {
      const data = await res.json();
      message = data.detail || data.message || message;
    } catch {
      // ignore non-JSON error bodies
    }
    throw new Error(typeof message === "string" ? message : JSON.stringify(message));
  }
  const blob = await res.blob();
  const header = res.headers.get("Content-Disposition");
  const match = header ? /filename="([^"]+)"/.exec(header) : null;
  const filename = match?.[1] || fallbackFilename;
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
  return { filename };
}

export async function downloadEntityTemplateFromEntity({
  kind,
  entityId,
  filename,
  includeMemory = false,
}) {
  const res = await fetch("/api/entity-templates/export-from-entity", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      kind,
      entity_id: entityId,
      filename,
      include_memory: includeMemory,
    }),
  });
  return downloadAttachmentResponse(res, filename || "entity-template.json");
}

export async function downloadEntityTemplateFile(templateId) {
  const res = await fetch(
    `/api/entity-templates/${encodeURIComponent(templateId)}/download`,
  );
  return downloadAttachmentResponse(res, `${templateId}.json`);
}

export async function postSpawnEntityFromTemplate(template, { position, areaId = null }) {
  const res = await fetch("/api/entity-templates/spawn-from-template", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      template,
      position,
      area_id: areaId,
    }),
  });
  const data = await res.json();
  if (!res.ok || !data.ok) {
    throw new Error(data.detail || data.message || `HTTP ${res.status}`);
  }
  return data;
}

export async function postSpawnEntityTemplate(templateId, { position, areaId = null }) {
  const res = await fetch(
    `/api/entity-templates/${encodeURIComponent(templateId)}/spawn`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        position,
        area_id: areaId,
      }),
    },
  );
  const data = await res.json();
  if (!res.ok || !data.ok) {
    throw new Error(data.detail || data.message || `HTTP ${res.status}`);
  }
  return data;
}

export async function deleteEntityTemplate(templateId) {
  const res = await fetch(
    `/api/entity-templates/${encodeURIComponent(templateId)}`,
    { method: "DELETE" },
  );
  const data = await res.json();
  if (!res.ok || !data.ok) {
    throw new Error(data.detail || data.message || `HTTP ${res.status}`);
  }
  return data;
}

export async function importEntityTemplate({ filename, template }) {
  const res = await fetch("/api/entity-templates/import", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ filename, template }),
  });
  const data = await res.json();
  if (!res.ok || !data.ok) {
    throw new Error(data.detail || data.message || `HTTP ${res.status}`);
  }
  return data;
}

export async function fetchAreaTemplates() {
  const res = await fetch("/api/area-templates");
  const data = await res.json();
  if (!res.ok || !data.ok) {
    throw new Error(data.message || `GET /api/area-templates failed: HTTP ${res.status}`);
  }
  return data;
}

export async function postSaveAreaTemplate({
  areaId,
  filename,
  name = null,
  includeHiddenObjects = true,
}) {
  const res = await fetch("/api/area-templates/save-from-area", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      area_id: areaId,
      filename,
      name,
      include_hidden_objects: includeHiddenObjects,
    }),
  });
  const data = await res.json();
  if (!res.ok || !data.ok) {
    throw new Error(data.detail || data.message || `HTTP ${res.status}`);
  }
  return data;
}

export async function downloadAreaTemplateFromArea({
  areaId,
  filename,
  name = null,
  includeHiddenObjects = true,
}) {
  const res = await fetch("/api/area-templates/export-from-area", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      area_id: areaId,
      filename,
      name,
      include_hidden_objects: includeHiddenObjects,
    }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || data.message || `HTTP ${res.status}`);
  }
  const blob = await res.blob();
  const disposition = res.headers.get("content-disposition") || "";
  const match = disposition.match(/filename="([^"]+)"/);
  const resolvedName = match?.[1] || filename;
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = resolvedName;
  anchor.click();
  URL.revokeObjectURL(url);
  return { filename: resolvedName };
}

export async function downloadAreaTemplateFile(templateId) {
  const res = await fetch(
    `/api/area-templates/${encodeURIComponent(templateId)}/download`,
  );
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || data.message || `HTTP ${res.status}`);
  }
  const blob = await res.blob();
  const disposition = res.headers.get("content-disposition") || "";
  const match = disposition.match(/filename="([^"]+)"/);
  const filename = match?.[1] || `${templateId}.json`;
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
  return { filename };
}

export async function postSpawnAreaFromTemplate(template, { areaId, mode = "new" }) {
  const res = await fetch("/api/area-templates/spawn-from-template", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ template, area_id: areaId, mode }),
  });
  const data = await res.json();
  if (!res.ok || !data.ok) {
    throw new Error(data.detail || data.message || `HTTP ${res.status}`);
  }
  return data;
}

export async function postSpawnAreaTemplate(templateId, { areaId, mode = "new" }) {
  const res = await fetch(
    `/api/area-templates/${encodeURIComponent(templateId)}/spawn`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ area_id: areaId, mode }),
    },
  );
  const data = await res.json();
  if (!res.ok || !data.ok) {
    throw new Error(data.detail || data.message || `HTTP ${res.status}`);
  }
  return data;
}

export async function deleteAreaTemplate(templateId) {
  const res = await fetch(
    `/api/area-templates/${encodeURIComponent(templateId)}`,
    { method: "DELETE" },
  );
  const data = await res.json();
  if (!res.ok || !data.ok) {
    throw new Error(data.detail || data.message || `HTTP ${res.status}`);
  }
  return data;
}

export async function importAreaTemplate({ filename, template }) {
  const res = await fetch("/api/area-templates/import", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ filename, template }),
  });
  const data = await res.json();
  if (!res.ok || !data.ok) {
    throw new Error(data.detail || data.message || `HTTP ${res.status}`);
  }
  return data;
}

export async function uploadPlugin(file) {
  const form = new FormData();
  form.append("file", file, file.name);
  const res = await fetch("/api/plugins/upload", {
    method: "POST",
    body: form,
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || `HTTP ${res.status}`);
  }
  return data;
}

export async function getLorebooks() {
  const res = await fetch("/api/lorebooks");
  const data = await res.json();
  if (!res.ok || !data.ok) {
    throw new Error(data.message || `GET /api/lorebooks failed: HTTP ${res.status}`);
  }
  return data;
}

export async function createLorebook(payload = {}) {
  const res = await fetch("/api/lorebooks", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) {
    const detail = data.detail || data.message || `HTTP ${res.status}`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

export async function loadDemoLorebook() {
  const res = await fetch("/api/lorebooks/load-demo", { method: "POST" });
  const data = await res.json();
  if (!res.ok) {
    const detail = data.detail || data.message || `HTTP ${res.status}`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

export async function getLorebook(bookId) {
  const res = await fetch(`/api/lorebooks/${encodeURIComponent(bookId)}`);
  const data = await res.json();
  if (!res.ok) {
    const detail = data.detail || data.message || `HTTP ${res.status}`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

export async function putLorebook(bookId, lorebook) {
  const res = await fetch(`/api/lorebooks/${encodeURIComponent(bookId)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(lorebook),
  });
  const data = await res.json();
  if (!res.ok) {
    const detail = data.detail || data.message || `HTTP ${res.status}`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

export async function deleteLorebook(bookId) {
  const res = await fetch(`/api/lorebooks/${encodeURIComponent(bookId)}`, {
    method: "DELETE",
  });
  const data = await res.json();
  if (!res.ok) {
    const detail = data.detail || data.message || `HTTP ${res.status}`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

export async function getLorebookScanConfig(agentId) {
  const query = agentId ? `?agent_id=${encodeURIComponent(agentId)}` : "";
  const res = await fetch(`/api/lorebooks/scan-config${query}`);
  const data = await res.json();
  if (!res.ok) {
    const detail = data.detail || data.message || `HTTP ${res.status}`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

export async function putLorebookScanConfig(config) {
  const res = await fetch("/api/lorebooks/scan-config", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
  const data = await res.json();
  if (!res.ok) {
    const detail = data.detail || data.message || `HTTP ${res.status}`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

export async function downloadLorebook(bookId) {
  const res = await fetch(`/api/lorebooks/${encodeURIComponent(bookId)}/download`);
  if (!res.ok) {
    let message = `HTTP ${res.status}`;
    try {
      const data = await res.json();
      message = data.detail || data.message || message;
    } catch {
      // ignore non-JSON error bodies
    }
    throw new Error(typeof message === "string" ? message : JSON.stringify(message));
  }
  const blob = await res.blob();
  const disposition = res.headers.get("Content-Disposition") || "";
  const match = disposition.match(/filename="([^"]+)"/);
  const filename = match?.[1] || `${bookId}.lorebook.json`;
  return { blob, filename };
}

export async function uploadLorebook(file) {
  const form = new FormData();
  form.append("file", file, file.name);
  const res = await fetch("/api/lorebooks/upload", {
    method: "POST",
    body: form,
  });
  const data = await res.json();
  if (!res.ok) {
    const detail = data.detail || data.message || `HTTP ${res.status}`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

export async function postCreateDecoration(body) {
  const res = await fetch("/api/decorations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) {
    const detail = data.detail || data.message || `HTTP ${res.status}`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

export async function updateDecoration(body) {
  const res = await fetch("/api/decorations", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) {
    const detail = data.detail || data.message || `HTTP ${res.status}`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

export async function deleteDecoration(body) {
  const res = await fetch("/api/decorations", {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) {
    const detail = data.detail || data.message || `HTTP ${res.status}`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

export async function reorderDecoration(body) {
  const res = await fetch("/api/decorations/reorder", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) {
    const detail = data.detail || data.message || `HTTP ${res.status}`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

export async function uploadDecorationAsset(file) {
  const form = new FormData();
  form.append("file", file, file.name);
  const res = await fetch("/api/decoration-assets/upload", {
    method: "POST",
    body: form,
  });
  const data = await res.json();
  if (!res.ok) {
    const detail = data.detail || data.message || `HTTP ${res.status}`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}
