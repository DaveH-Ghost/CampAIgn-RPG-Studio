/**
 * Sidebar panels: passive vision, turn log, recent events (V0.3.1e–0.4.0c2).
 */

const MAX_LOG_ENTRIES = 50;

let turnLogEntries = [];
let lastPromptText = null;
let lastResponseText = null;
let lastResponseTokens = null;

function formatTokenMeta(tokens) {
  if (!tokens) return "";
  const lines = [];
  const input = tokens.prompt != null ? Number(tokens.prompt).toLocaleString() : "—";
  const output = tokens.completion != null ? Number(tokens.completion).toLocaleString() : "—";
  const total = tokens.total != null ? Number(tokens.total).toLocaleString() : "—";
  lines.push(`Input (API): ${input}`);
  lines.push(`Output (API): ${output}`);
  lines.push(`Total (API): ${total}`);
  if (tokens.estimate != null) {
    const est = Number(tokens.estimate).toLocaleString();
    if (tokens.prompt != null) {
      lines.push(`Pre-turn estimate: ~${est} input tokens`);
      lines.push(`Estimate vs actual input: ~${est} → ${input}`);
    } else {
      lines.push(`Pre-turn estimate: ~${est} input tokens`);
    }
  }
  return lines.join("\n");
}

export function renderPassiveVision(snapshot, visionEl, emptyEl) {
  const text = snapshot?.passive_vision?.trim();
  if (!text) {
    visionEl.textContent = "";
    visionEl.classList.add("hidden");
    emptyEl.classList.remove("hidden");
    return;
  }
  visionEl.textContent = text;
  visionEl.classList.remove("hidden");
  emptyEl.classList.add("hidden");
}

export function renderAgentsElsewhere(snapshot, listEl, emptyEl) {
  const activeAreaId = snapshot?.active_area_id;
  const agents = Array.isArray(snapshot?.agents) ? snapshot.agents : [];
  const elsewhere = agents.filter((a) => a.area_id && a.area_id !== activeAreaId);

  listEl.innerHTML = "";
  if (elsewhere.length === 0) {
    listEl.classList.add("hidden");
    emptyEl.classList.remove("hidden");
    return;
  }
  listEl.classList.remove("hidden");
  emptyEl.classList.add("hidden");

  for (const agent of elsewhere) {
    const item = document.createElement("li");
    const name = document.createElement("span");
    name.textContent = agent.name;
    const area = document.createElement("span");
    area.className = "agents-elsewhere-area";
    area.textContent = ` — ${agent.area_id}`;
    item.appendChild(name);
    item.appendChild(area);
    listEl.appendChild(item);
  }
}

export function renderRecentEvents(snapshot, listEl, emptyEl) {
  const events = snapshot?.recent_events;
  listEl.innerHTML = "";
  if (!Array.isArray(events) || events.length === 0) {
    emptyEl.classList.remove("hidden");
    return;
  }
  emptyEl.classList.add("hidden");
  for (const event of [...events].reverse()) {
    const item = document.createElement("li");
    item.className = "recent-event-entry";
    const turn = document.createElement("span");
    turn.className = "recent-event-turn";
    turn.textContent = `Turn ${event.session_turn}`;
    const text = document.createElement("span");
    text.className = "recent-event-text";
    text.textContent = event.text;
    item.appendChild(turn);
    item.appendChild(text);
    listEl.appendChild(item);
  }
}

export function appendTurnLogEntry({ sessionTurn, agentName, message, steps }) {
  turnLogEntries.unshift({
    sessionTurn,
    agentName,
    message,
    steps: Array.isArray(steps) ? steps : [],
  });
  if (turnLogEntries.length > MAX_LOG_ENTRIES) {
    turnLogEntries.length = MAX_LOG_ENTRIES;
  }
}

export function clearTurnLog() {
  turnLogEntries = [];
}

export function renderTurnLog(listEl, emptyEl) {
  listEl.innerHTML = "";
  if (turnLogEntries.length === 0) {
    emptyEl.classList.remove("hidden");
    return;
  }
  emptyEl.classList.add("hidden");

  for (const entry of turnLogEntries) {
    const item = document.createElement("li");
    item.className = "turn-log-entry";

    const head = document.createElement("div");
    head.className = "turn-log-head";
    head.textContent = `Session ${entry.sessionTurn} — ${entry.agentName}`;
    item.appendChild(head);

    const composite = document.createElement("p");
    composite.className = "turn-log-composite";
    composite.textContent = entry.message;
    item.appendChild(composite);

    if (entry.steps.length > 0) {
      const steps = document.createElement("ul");
      steps.className = "turn-log-steps";
      for (const step of entry.steps) {
        const li = document.createElement("li");
        li.textContent = `[${step.kind}] ${step.result}`;
        steps.appendChild(li);
      }
      item.appendChild(steps);
    }

    listEl.appendChild(item);
  }
}

export function setLastPrompt(text) {
  lastPromptText = text ?? null;
}

export function renderLastPrompt(promptEl, emptyEl) {
  if (!lastPromptText) {
    promptEl.textContent = "";
    promptEl.classList.add("hidden");
    emptyEl.classList.remove("hidden");
    return;
  }
  promptEl.textContent = lastPromptText;
  promptEl.classList.remove("hidden");
  emptyEl.classList.add("hidden");
}

export function bindPromptDebug(detailsEl, promptEl, emptyEl, fetchPromptFn) {
  detailsEl.addEventListener("toggle", async () => {
    if (!detailsEl.open) return;
    if (lastPromptText) {
      renderLastPrompt(promptEl, emptyEl);
      return;
    }
    try {
      const data = await fetchPromptFn();
      if (data.ok && data.prompt) {
        setLastPrompt(data.prompt);
      }
      renderLastPrompt(promptEl, emptyEl);
    } catch {
      renderLastPrompt(promptEl, emptyEl);
    }
  });
}

function formatResponseText(text) {
  const trimmed = String(text ?? "").trim();
  if (!trimmed) return "";
  try {
    return JSON.stringify(JSON.parse(trimmed), null, 2);
  } catch {
    return trimmed;
  }
}

export function setLastResponse(text, tokens = null) {
  lastResponseText = text ?? null;
  lastResponseTokens = tokens ?? null;
}

export function renderLastResponse(responseEl, emptyEl, tokensEl = null) {
  if (!lastResponseText) {
    responseEl.textContent = "";
    responseEl.classList.add("hidden");
    emptyEl.classList.remove("hidden");
    if (tokensEl) {
      tokensEl.textContent = "";
      tokensEl.classList.add("hidden");
    }
    return;
  }
  if (tokensEl) {
    const meta = formatTokenMeta(lastResponseTokens);
    if (meta) {
      tokensEl.textContent = meta;
      tokensEl.classList.remove("hidden");
    } else {
      tokensEl.textContent = "";
      tokensEl.classList.add("hidden");
    }
  }
  responseEl.textContent = formatResponseText(lastResponseText);
  responseEl.classList.remove("hidden");
  emptyEl.classList.add("hidden");
}

export function bindResponseDebug(detailsEl, responseEl, emptyEl, tokensEl = null) {
  detailsEl.addEventListener("toggle", () => {
    if (!detailsEl.open) return;
    renderLastResponse(responseEl, emptyEl, tokensEl);
  });
}
