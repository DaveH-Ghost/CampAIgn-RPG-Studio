/** Player API client for /play/generic. */

const SEAT_KEY = "campaign_play_seat";

/** In-memory fallback when sessionStorage is blocked (private / strict browsers). */
let memorySeat = null;

function storageGet() {
  try {
    return sessionStorage.getItem(SEAT_KEY);
  } catch {
    return null;
  }
}

function storageSet(value) {
  try {
    sessionStorage.setItem(SEAT_KEY, value);
    return true;
  } catch {
    return false;
  }
}

function storageClear() {
  try {
    sessionStorage.removeItem(SEAT_KEY);
  } catch {
    // ignore
  }
}

function stripSeatFromUrl() {
  try {
    const params = new URLSearchParams(window.location.search);
    if (!params.has("seat")) return;
    params.delete("seat");
    const next = `${window.location.pathname}${params.toString() ? `?${params}` : ""}${window.location.hash}`;
    window.history.replaceState({}, "", next);
  } catch {
    // ignore — leave ?seat= in the URL if history is blocked
  }
}

export function loadSeatToken() {
  const params = new URLSearchParams(window.location.search);
  const fromQuery = params.get("seat");
  if (fromQuery) {
    memorySeat = fromQuery;
    storageSet(fromQuery);
    stripSeatFromUrl();
    return fromQuery;
  }
  return memorySeat || storageGet();
}

export function clearSeatToken() {
  memorySeat = null;
  storageClear();
}

function authHeaders(token) {
  return {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  };
}

async function playerFetch(token, path, options = {}) {
  const res = await fetch(path, {
    ...options,
    headers: {
      ...authHeaders(token),
      ...(options.headers || {}),
    },
  });
  const data = await res.json().catch(() => ({}));
  if (res.status === 401) {
    const err = new Error(
      typeof data.detail === "string"
        ? data.detail
        : data.detail?.message || "Seat expired or invalid.",
    );
    err.code = 401;
    throw err;
  }
  if (!res.ok) {
    const detail = data.detail;
    const message =
      typeof detail === "string"
        ? detail
        : detail?.message || data.message || `HTTP ${res.status}`;
    const err = new Error(message);
    err.status = res.status;
    if (detail && typeof detail === "object" && detail.concurrency_limit_exceeded) {
      err.concurrency_limit_exceeded = true;
    }
    if (data.concurrency_limit_exceeded) {
      err.concurrency_limit_exceeded = true;
    }
    throw err;
  }
  return data;
}

export async function fetchPlayerView(token) {
  return playerFetch(token, "/api/player/view");
}

export async function fetchPlayerMe(token) {
  return playerFetch(token, "/api/player/me");
}

export async function postPlayerTurn(token, compoundTurn) {
  return playerFetch(token, "/api/player/turn", {
    method: "POST",
    body: JSON.stringify({ compound_turn: compoundTurn }),
  });
}

export function buildPlayTurn({
  reasoning = "Player turn.",
  move = null,
  look = null,
  say = null,
  action = "none",
  target = null,
  verb = null,
} = {}) {
  const payload = { reasoning, action };
  if (move) payload.move = String(move).trim();
  if (look) payload.look = String(look).trim();
  if (say) payload.say = String(say).trim();
  if (action === "interact") {
    payload.target = String(target || "").trim();
    payload.verb = String(verb || "").trim();
  } else if (action === "emote") {
    payload.verb = String(verb || "").trim();
    if (target) payload.target = String(target).trim();
  } else if (action === "verb") {
    payload.verb = String(verb || "").trim();
    if (target) payload.target = String(target).trim();
  }
  return payload;
}
