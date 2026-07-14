/**
 * Help popover for interact result/passive template placeholders.
 */

let cachedVars = null;

export function clearInteractTemplateVarsCache() {
  cachedVars = null;
}

export async function fetchInteractTemplateVars() {
  if (cachedVars) return cachedVars;
  const res = await fetch("/api/interact-template-vars");
  if (!res.ok) {
    throw new Error(`GET /api/interact-template-vars failed: HTTP ${res.status}`);
  }
  const data = await res.json();
  cachedVars = data.vars || [];
  return cachedVars;
}

function closePopover(popover) {
  popover.classList.add("hidden");
  document.removeEventListener("click", popover._outsideClick, true);
  document.removeEventListener("keydown", popover._escapeKey, true);
}

function openPopover(popover, anchor) {
  popover.classList.remove("hidden");
  const rect = anchor.getBoundingClientRect();
  popover.style.left = `${Math.min(rect.left, window.innerWidth - 320)}px`;
  popover.style.top = `${rect.bottom + 6}px`;

  popover._outsideClick = (event) => {
    if (!popover.contains(event.target) && event.target !== anchor) {
      closePopover(popover);
    }
  };
  popover._escapeKey = (event) => {
    if (event.key === "Escape") closePopover(popover);
  };
  document.addEventListener("click", popover._outsideClick, true);
  document.addEventListener("keydown", popover._escapeKey, true);
}

/**
 * Append a ? button beside a field label; click shows placeholder help.
 * @param {HTMLElement} labelSpan
 */
export function attachTemplateVarHelp(labelSpan) {
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "template-var-help-btn";
  btn.textContent = "?";
  btn.setAttribute("aria-label", "Show template variable help");
  btn.title = "Template variables";

  const popover = document.createElement("div");
  popover.className = "template-var-popover hidden";
  popover.setAttribute("role", "dialog");
  popover.setAttribute("aria-label", "Template variables");

  const heading = document.createElement("p");
  heading.className = "template-var-popover-heading";
  heading.textContent = "Use these in result and passive text:";
  popover.appendChild(heading);

  const list = document.createElement("ul");
  list.className = "template-var-list";
  popover.appendChild(list);

  document.body.appendChild(popover);

  btn.addEventListener("click", async (event) => {
    event.preventDefault();
    event.stopPropagation();
    if (!popover.classList.contains("hidden")) {
      closePopover(popover);
      return;
    }
    try {
      // Always refresh so enabling/disabling plugins updates the list.
      clearInteractTemplateVarsCache();
      const vars = await fetchInteractTemplateVars();
      list.innerHTML = "";
      for (const item of vars) {
        const li = document.createElement("li");
        if (item.source === "plugin") {
          li.classList.add("template-var-plugin");
          const pluginLabel = item.plugin_label || item.plugin_id || "plugin";
          li.title = `From plugin: ${pluginLabel}`;
        }
        const code = document.createElement("code");
        code.textContent = item.placeholder;
        li.appendChild(code);
        const desc = document.createElement("span");
        desc.textContent = item.description;
        li.appendChild(desc);
        list.appendChild(li);
      }
      openPopover(popover, btn);
    } catch (err) {
      list.innerHTML = "";
      const li = document.createElement("li");
      li.textContent = String(err.message || err);
      list.appendChild(li);
      openPopover(popover, btn);
    }
  });

  labelSpan.appendChild(btn);
}
