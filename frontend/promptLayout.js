/**
 * Prompt layout editor — block list, reorder, edit, add/remove (V0.4.1c).
 */

import {
  getLorebooks,
  getPrompt,
  getPromptBlockCatalog,
  getPromptBlocks,
  getPromptSlots,
  previewPromptBlocks,
  putPromptBlocks,
  resetPromptBlocks,
} from "./api.js";

let showToast = () => {};
let getActiveAgentId = () => null;
let onPreviewUpdated = async () => {};

/** @type {Array<{ name: string, description?: string, preview?: string }>} */
let slotCatalog = [];
/** @type {Array<{ type: string, label: string, description?: string, options?: object[], default_content?: string }>} */
let blockTypeCatalog = [];
/** @type {Record<string, { label?: string, fields: Array<{ key: string, label: string, default?: boolean }>, min_enabled?: number }>} */
let slotSettings = {};
/** @type {object[]} */
let workingBlocks = [];
let usesDefault = true;
let dirty = false;
let openSettingsIndex = null;

let detailsEl;
let listEl;
let statusEl;
let previewBackdropEl;
let previewBodyEl;
let previewCloseBtn;
let saveBtn;
let resetBtn;
let showPreviewBtn;
let addTypeSelect;
let addVariantWrap;
let addVariantLabel;
let addVariantSelect;
let addContentWrap;
let addContentInput;
let addLorebookWrap;
let addLorebookIdSelect;
let addBtn;

export function initPromptLayout({
  detailsEl: details,
  listEl: list,
  statusEl: status,
  saveBtn: save,
  resetBtn: reset,
  showPreviewBtn: showPreview,
  previewBackdropEl: previewBackdrop,
  previewBodyEl: previewBody,
  previewCloseBtn: previewClose,
  addTypeSelect: addType,
  addVariantWrap: variantWrap,
  addVariantLabel: variantLabel,
  addVariantSelect: variantSelect,
  addContentWrap: contentWrap,
  addContentInput: contentInput,
  addLorebookWrap: lorebookWrap,
  addLorebookIdSelect: lorebookIdSelect,
  addBtn: addButton,
  showToastFn,
  getActiveAgentIdFn,
  onPreviewUpdatedFn,
}) {
  detailsEl = details;
  listEl = list;
  statusEl = status;
  saveBtn = save;
  resetBtn = reset;
  showPreviewBtn = showPreview;
  previewBackdropEl =
    previewBackdrop ?? document.getElementById("prompt-preview-backdrop");
  previewBodyEl = previewBody ?? document.getElementById("prompt-preview-body");
  previewCloseBtn =
    previewClose ?? document.getElementById("prompt-preview-close");
  addTypeSelect = addType;
  addVariantWrap = variantWrap;
  addVariantLabel = variantLabel;
  addVariantSelect = variantSelect;
  addContentWrap = contentWrap;
  addContentInput = contentInput;
  addLorebookWrap = lorebookWrap;
  addLorebookIdSelect = lorebookIdSelect;
  addBtn = addButton;
  showToast = showToastFn;
  getActiveAgentId = getActiveAgentIdFn;
  onPreviewUpdated = onPreviewUpdatedFn ?? onPreviewUpdated;

  saveBtn?.addEventListener("click", () => {
    void saveLayout();
  });
  resetBtn?.addEventListener("click", () => {
    void resetLayout();
  });
  showPreviewBtn?.addEventListener("click", () => {
    void showFullPromptPreview();
  });
  previewCloseBtn?.addEventListener("click", () => {
    closeFullPromptPreview();
  });
  previewBackdropEl?.addEventListener("click", (e) => {
    if (e.target === previewBackdropEl) {
      closeFullPromptPreview();
    }
  });
  addBtn?.addEventListener("click", () => {
    addBlockFromForm().catch((err) => showToast(String(err.message || err), true));
  });
  addTypeSelect?.addEventListener("change", () => syncAddBlockForm());
  addVariantSelect?.addEventListener("change", () => syncVariantSubform());
  document.addEventListener("click", (e) => {
    if (openSettingsIndex == null) return;
    if (e.target.closest(".prompt-block-settings-popover")) return;
    if (e.target.closest(".prompt-block-settings-btn")) return;
    closeSlotSettings();
  });
  detailsEl?.addEventListener("toggle", () => {
    if (detailsEl.open) {
      loadEditor();
    }
  });
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    if (!previewBackdropEl || previewBackdropEl.classList.contains("hidden")) return;
    closeFullPromptPreview();
  });
}

export async function reloadPromptLayoutIfOpen() {
  if (detailsEl?.open) {
    await loadEditor();
  }
}

async function loadEditor() {
  statusEl.textContent = "Loading…";
  try {
    const agentId = getActiveAgentId();
    const [blocksData, slotsData, catalogData] = await Promise.all([
      getPromptBlocks(agentId),
      getPromptSlots(agentId),
      getPromptBlockCatalog(),
    ]);
    if (!blocksData.ok) throw new Error(blocksData.message);
    if (!slotsData.ok) throw new Error(slotsData.message);
    if (!catalogData.ok) throw new Error(catalogData.message);
    workingBlocks = blocksData.blocks.map((block) => ({ ...block }));
    usesDefault = !!blocksData.uses_default;
    dirty = false;
    slotCatalog = slotsData.slots || [];
    blockTypeCatalog = catalogData.block_types || [];
    slotSettings = catalogData.slot_settings || {};
    closeSlotSettings();
    populateAddTypeSelect();
    syncAddBlockForm();
    renderBlockList();
    updateStatus();
    await refreshPreview({ quiet: true });
  } catch (err) {
    statusEl.textContent = String(err.message || err);
    showToast(String(err.message || err), true);
  }
}

function catalogEntryForType(type) {
  return blockTypeCatalog.find((entry) => entry.type === type);
}

function populateAddTypeSelect() {
  addTypeSelect.innerHTML = "";
  for (const entry of blockTypeCatalog) {
    const option = document.createElement("option");
    option.value = entry.type;
    option.textContent = entry.label || entry.type;
    addTypeSelect.appendChild(option);
  }
}

function syncVariantSubform() {
  const type = addTypeSelect.value;
  const variant = addVariantSelect?.value || "";
  const isLorebookSlot = type === "slot" && variant === "lorebook";
  addLorebookWrap?.classList.toggle("hidden", !isLorebookSlot);
  if (isLorebookSlot) {
    void populateLorebookIdSelect();
  }
}

function syncAddBlockForm() {
  const type = addTypeSelect.value;
  const entry = catalogEntryForType(type);
  const variant = addVariantSelect?.value || "";
  const isLorebookSlot = type === "slot" && variant === "lorebook";
  addVariantWrap.classList.toggle("hidden", type === "text");
  addContentWrap.classList.toggle("hidden", type !== "text");
  addLorebookWrap?.classList.toggle("hidden", !isLorebookSlot);

  if (type === "text") {
    addContentInput.value = entry?.default_content ?? "";
    return;
  }

  addVariantSelect.innerHTML = "";
  const options = entry?.options || [];
  addVariantLabel.textContent =
    type === "plugin_slot" ? "Plugin slot" : type === "slot" ? "Slot" : "Section";
  for (const item of options) {
    const option = document.createElement("option");
    option.value = item.name;
    option.textContent = item.description ? `${item.name} — ${item.description}` : item.name;
    addVariantSelect.appendChild(option);
  }
  if (isLorebookSlot) {
    void populateLorebookIdSelect();
  }
}

async function populateLorebookIdSelect() {
  if (!addLorebookIdSelect) return;
  addLorebookIdSelect.innerHTML = "";
  try {
    const data = await getLorebooks();
    const books = data.lorebooks || [];
    if (books.length === 0) {
      const option = document.createElement("option");
      option.value = "";
      option.textContent = "(load a lorebook first)";
      addLorebookIdSelect.appendChild(option);
      return;
    }
    for (const book of books) {
      const option = document.createElement("option");
      option.value = book.id;
      option.textContent = `${book.name} (${book.id})`;
      addLorebookIdSelect.appendChild(option);
    }
  } catch (err) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = String(err.message || err);
    addLorebookIdSelect.appendChild(option);
  }
}

function slotMeta(name) {
  return slotCatalog.find((s) => s.name === name) || { name, preview: "", description: "" };
}

function slotSettingsSchema(block) {
  if (block.type !== "slot" || !block.name) return null;
  return slotSettings[block.name] || null;
}

function isSlotLikeBlock(block) {
  return block.type === "slot" || block.type === "plugin_slot";
}

function resolvedSlotOptions(block, schema) {
  const options = { ...(block.options || {}) };
  for (const field of schema.fields) {
    if (!(field.key in options)) {
      options[field.key] = field.default ?? false;
    }
  }
  return options;
}

function countEnabledSlotOptions(options, schema) {
  return schema.fields.filter((field) => options[field.key]).length;
}

function closeSlotSettings() {
  openSettingsIndex = null;
}

function toggleSlotSettings(index) {
  openSettingsIndex = openSettingsIndex === index ? null : index;
  renderBlockList();
}

async function applySlotOptions(index, nextOptions, schema) {
  if (countEnabledSlotOptions(nextOptions, schema) < (schema.min_enabled ?? 0)) {
    showToast("At least one option must stay enabled.", true);
    return;
  }
  collectBlocksFromDom();
  const normalized = { ...nextOptions };
  const allDefault = schema.fields.every(
    (field) => normalized[field.key] === (field.default ?? false),
  );
  workingBlocks[index] = {
    ...workingBlocks[index],
    options: allDefault ? undefined : normalized,
  };
  markDirty();
  await mergeSlotPreviewsFromApi();
  renderBlockList();
  openSettingsIndex = index;
}

async function mergeSlotPreviewsFromApi() {
  const agentId = getActiveAgentId();
  const result = await previewPromptBlocks(blocksPayload(), agentId);
  if (!result.ok) throw new Error(result.message);
  for (let i = 0; i < workingBlocks.length; i += 1) {
    const preview = result.blocks[i]?.preview;
    if (preview !== undefined && workingBlocks[i] && isSlotLikeBlock(workingBlocks[i])) {
      workingBlocks[i] = { ...workingBlocks[i], preview };
    }
  }
}

function blockSlotPreview(block) {
  if (block.preview !== undefined && block.preview !== null) {
    return block.preview || "(empty)";
  }
  return slotMeta(block.name).preview || "(empty)";
}

function buildSlotSettingsPopover(block, index, schema) {
  const popover = document.createElement("div");
  popover.className = "prompt-block-settings-popover";
  const title = document.createElement("div");
  title.className = "prompt-block-settings-title";
  title.textContent = schema.label || block.name;
  popover.appendChild(title);

  const options = resolvedSlotOptions(block, schema);
  for (const field of schema.fields) {
    const label = document.createElement("label");
    label.className = "prompt-block-settings-field";
    const input = document.createElement("input");
    input.type = "checkbox";
    input.checked = !!options[field.key];
    input.addEventListener("change", () => {
      const next = resolvedSlotOptions(block, schema);
      next[field.key] = input.checked;
      applySlotOptions(index, next, schema).catch((err) => {
        showToast(String(err.message || err), true);
        input.checked = !input.checked;
      });
    });
    const span = document.createElement("span");
    span.textContent = field.label;
    label.appendChild(input);
    label.appendChild(span);
    popover.appendChild(label);
  }
  return popover;
}

function markDirty() {
  dirty = true;
  updateStatus();
}

function updateStatus() {
  if (dirty) {
    statusEl.textContent = "Unsaved changes — click Save layout.";
    return;
  }
  statusEl.textContent = usesDefault ? "Using profile default layout." : "Custom layout saved.";
}

function renderBlockList() {
  const keepOpen = openSettingsIndex;
  listEl.innerHTML = "";
  workingBlocks.forEach((block, index) => {
    listEl.appendChild(buildBlockRow(block, index));
  });
  openSettingsIndex = keepOpen;
}

function buildBlockRow(block, index) {
  const li = document.createElement("li");
  li.className = "prompt-block-item";

  const main = document.createElement("div");
  main.className = "prompt-block-main";

  if (block.type === "slot" || block.type === "plugin_slot") {
    const meta = slotMeta(block.name);
    const label = document.createElement("div");
    label.className = "prompt-block-label";
    const prefix = block.type === "plugin_slot" ? "Plugin slot" : "Slot";
    const lorebookId = block.options?.lorebook_id;
    label.textContent = lorebookId
      ? `${prefix}: ${block.name} (${lorebookId})`
      : `${prefix}: ${block.name}`;
    const desc = document.createElement("div");
    desc.className = "prompt-block-desc";
    desc.textContent = meta.description || "";
    const preview = document.createElement("pre");
    preview.className = "prompt-block-preview";
    preview.textContent = blockSlotPreview(block);
    main.appendChild(label);
    if (meta.description) main.appendChild(desc);
    main.appendChild(preview);
  } else if (block.type === "text") {
    const label = document.createElement("label");
    label.className = "prompt-block-field";
    const span = document.createElement("span");
    span.textContent = "Text";
    const textarea = document.createElement("textarea");
    textarea.className = "prompt-block-textarea";
    textarea.rows = 2;
    textarea.value = block.content ?? "";
    textarea.dataset.blockIndex = String(index);
    textarea.addEventListener("input", markDirty);
    label.appendChild(span);
    label.appendChild(textarea);
    main.appendChild(label);
  } else if (block.type === "section") {
    const label = document.createElement("label");
    label.className = "prompt-block-field";
    const span = document.createElement("span");
    span.textContent = `Section: ${block.name}`;
    const textarea = document.createElement("textarea");
    textarea.className = "prompt-block-textarea prompt-block-textarea-section";
    textarea.rows = 5;
    textarea.value = block.content ?? "";
    textarea.dataset.blockIndex = String(index);
    textarea.addEventListener("input", markDirty);
    label.appendChild(span);
    label.appendChild(textarea);
    main.appendChild(label);
  } else {
    const label = document.createElement("div");
    label.className = "prompt-block-label";
    label.textContent = `Unknown block type: ${block.type}`;
    main.appendChild(label);
  }

  li.appendChild(main);

  const moveCol = document.createElement("div");
  moveCol.className = "prompt-block-move-col";
  const upBtn = document.createElement("button");
  upBtn.type = "button";
  upBtn.textContent = "↑";
  upBtn.title = "Move up";
  upBtn.disabled = index === 0;
  upBtn.addEventListener("click", () => {
    closeSlotSettings();
    moveBlock(index, -1);
  });
  const downBtn = document.createElement("button");
  downBtn.type = "button";
  downBtn.textContent = "↓";
  downBtn.title = "Move down";
  downBtn.disabled = index === workingBlocks.length - 1;
  downBtn.addEventListener("click", () => {
    closeSlotSettings();
    moveBlock(index, 1);
  });
  const removeBtn = document.createElement("button");
  removeBtn.type = "button";
  removeBtn.className = "prompt-block-remove";
  removeBtn.textContent = "×";
  removeBtn.title = "Remove block";
  removeBtn.disabled = workingBlocks.length <= 1;
  removeBtn.addEventListener("click", () => {
    closeSlotSettings();
    removeBlock(index);
  });
  moveCol.appendChild(upBtn);
  moveCol.appendChild(downBtn);
  moveCol.appendChild(removeBtn);

  const settingsSchema = slotSettingsSchema(block);
  if (settingsSchema) {
    const settingsBtn = document.createElement("button");
    settingsBtn.type = "button";
    settingsBtn.className = "prompt-block-settings-btn";
    settingsBtn.textContent = "⚙";
    settingsBtn.title = "Slot settings";
    settingsBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      toggleSlotSettings(index);
    });
    moveCol.appendChild(settingsBtn);
    if (openSettingsIndex === index) {
      moveCol.appendChild(buildSlotSettingsPopover(block, index, settingsSchema));
    }
  }

  li.appendChild(moveCol);

  return li;
}

function moveBlock(index, delta) {
  const target = index + delta;
  if (target < 0 || target >= workingBlocks.length) return;
  collectBlocksFromDom();
  const next = [...workingBlocks];
  const [moved] = next.splice(index, 1);
  next.splice(target, 0, moved);
  workingBlocks = next;
  markDirty();
  renderBlockList();
}

function removeBlock(index) {
  if (workingBlocks.length <= 1) {
    showToast("At least one prompt block is required.", true);
    return;
  }
  collectBlocksFromDom();
  workingBlocks = workingBlocks.filter((_, i) => i !== index);
  markDirty();
  renderBlockList();
}

function buildBlockFromCatalog(type, variantName, textContent) {
  const entry = catalogEntryForType(type);
  if (!entry) {
    throw new Error(`Unknown block type ${type}.`);
  }
  if (type === "slot") {
    const block = { type: "slot", name: variantName };
    if (variantName === "lorebook") {
      const bookId = addLorebookIdSelect?.value?.trim();
      if (!bookId) {
        throw new Error("Select a lorebook for the lorebook slot.");
      }
      block.options = { lorebook_id: bookId };
    }
    return block;
  }
  if (type === "plugin_slot") {
    if (!variantName) {
      throw new Error("Select a plugin slot.");
    }
    return { type: "plugin_slot", name: variantName };
  }
  if (type === "text") {
    return { type: "text", content: textContent ?? "" };
  }
  if (type === "section") {
    const option = (entry.options || []).find((item) => item.name === variantName);
    return {
      type: "section",
      name: variantName,
      content: option?.default_content ?? "",
    };
  }
  throw new Error(`Unsupported block type ${type}.`);
}

async function addBlockFromForm() {
  try {
    const type = addTypeSelect.value;
    const entry = catalogEntryForType(type);
    if (!entry) {
      throw new Error("Select a block type.");
    }
    collectBlocksFromDom();
    let block;
    if (type === "text") {
      block = buildBlockFromCatalog(type, null, addContentInput.value);
    } else {
      const variantName = addVariantSelect.value;
      if (!variantName) {
        throw new Error(
          type === "plugin_slot"
            ? "Select a plugin slot."
            : type === "slot"
              ? "Select a slot."
              : "Select a section.",
        );
      }
      block = buildBlockFromCatalog(type, variantName, null);
    }
    workingBlocks = [...workingBlocks, block];
    markDirty();
    if (isSlotLikeBlock(block)) {
      await mergeSlotPreviewsFromApi();
    }
    renderBlockList();
    if (type === "text") {
      addContentInput.value = entry.default_content ?? "";
    }
  } catch (err) {
    showToast(String(err.message || err), true);
  }
}

function collectBlocksFromDom() {
  const textareas = listEl.querySelectorAll("textarea[data-block-index]");
  for (const el of textareas) {
    const idx = Number(el.dataset.blockIndex);
    if (Number.isNaN(idx) || !workingBlocks[idx]) continue;
    workingBlocks[idx] = {
      ...workingBlocks[idx],
      content: el.value,
    };
  }
}

function blocksPayload() {
  collectBlocksFromDom();
  return workingBlocks.map((block) => {
    if (block.type === "slot") {
      const payload = { type: "slot", name: block.name };
      if (block.options && Object.keys(block.options).length > 0) {
        payload.options = block.options;
      }
      return payload;
    }
    if (block.type === "plugin_slot") {
      return { type: "plugin_slot", name: block.name };
    }
    if (block.type === "text") {
      return { type: "text", content: block.content ?? "" };
    }
    return {
      type: "section",
      name: block.name,
      content: block.content ?? "",
    };
  });
}

async function saveLayout() {
  try {
    const payload = blocksPayload();
    const result = await putPromptBlocks(payload);
    if (!result.ok) throw new Error(result.message);
    workingBlocks = result.blocks.map((b) => ({ ...b }));
    usesDefault = !!result.uses_default;
    dirty = false;
    renderBlockList();
    updateStatus();
    showToast("Prompt layout saved.", false);
    await refreshPreview();
  } catch (err) {
    showToast(String(err.message || err), true);
  }
}

async function resetLayout() {
  if (!window.confirm("Reset prompt layout to profile default?")) return;
  try {
    const result = await resetPromptBlocks();
    if (!result.ok) throw new Error(result.message);
    workingBlocks = result.blocks.map((b) => ({ ...b }));
    usesDefault = true;
    dirty = false;
    renderBlockList();
    updateStatus();
    showToast("Prompt layout reset.", false);
    await refreshPreview();
  } catch (err) {
    showToast(String(err.message || err), true);
  }
}

function closeFullPromptPreview() {
  previewBackdropEl?.classList.add("hidden");
}

async function showFullPromptPreview() {
  try {
    const prompt = await refreshPreview({ quiet: true });
    if (prompt == null) return;
    if (previewBodyEl) previewBodyEl.textContent = prompt;
    previewBackdropEl?.classList.remove("hidden");
  } catch (err) {
    showToast(String(err.message || err), true);
  }
}

async function refreshPreview({ quiet = false } = {}) {
  try {
    const agentId = getActiveAgentId();
    const data = await getPrompt(agentId);
    if (!data.ok) throw new Error(data.message);
    await mergeSlotPreviewsFromApi();
    renderBlockList();
    await onPreviewUpdated(data.prompt);
    if (!quiet) showToast("Prompt preview refreshed.", false);
    return data.prompt;
  } catch (err) {
    if (!quiet) showToast(String(err.message || err), true);
    return null;
  }
}

export { refreshPreview as refreshPromptPreview };
