# Changelog — CampAIgn-RPG-Studio

Studio is distributed via GitHub only (not PyPI). Version tags match `pyproject.toml`.

---

## 1.7.3

**Requires:** `campaign-rpg-engine>=1.7.3`

### Combat plugin

- New **Combat** plugin (`plugins/combat/`): HP/AC, equip/unequip weapons and armor, attack verbs while combat is active, unarmed (range 1, STR, 1d4).
- Start combat requires initiative on with a non-empty order; missing HP seeds to **10**. Downed (HP ≤ 0) removes the agent from initiative.
- GM panel **Start / End combat**; emit tags `[Combat Start]` / `[Combat End]` via the engine `area_event` hook.
- Prompt slot `combat` (place below inventory). Inventory shows `[equipped]` on equipped items; attack actions stay in the combat prompt.
- Object **Edit → Plugins**: set weapon/armor **stats** only (when Combat is enabled). Attack verbs + hit/miss text live under **Manage actions** (`combat_attack`); multiple verbs can share one weapon’s stats.
- Manage actions handler **`combat_attack`**: custom hit/miss templates with amber roll placeholders (`{attack_roll}`, `{damage_total}`, …).
- Combat panel: **Set max HP** for the active agent (fills current HP to max).

### Inventory GM setup

- Inventory panel: **Add object template to inventory** for the active agent (no dummy map object required).

### Plugin host

- `register_entity_form_section` + `GET /api/entity-form-sections` / `POST /api/entity-form-sections/merge` for plugin-driven create/edit form fields.

### Engine dependency

- Verb pathing honors explicit moves already in range; dynamic `path_range_from_turn` for weapon ranges.

---

## 1.7.2

**Requires:** `campaign-rpg-engine>=1.7.2`

### Featherless / concurrency UX

- Settings: **Concurrent LLM calls** checkbox — uncheck for one-at-a-time providers (sync memory consolidation; sequential affinity Call A/B).
- When the LLM provider returns a **concurrency limit** error, the GM gets a recovery modal: undo the last successful turn, optionally disable Concurrent LLM calls (recommended for Featherless).
- The modal also appears **as soon as background memory consolidation / affinity fails** with a concurrency limit (SSE `concurrency_limit`), not only on the next turn attempt.
- Play client shows a short toast pointing players at the GM when a seat turn hits the same limit.

### Fixes

- **Run turn ▶** re-enables correctly after a turn when initiative is off (was stuck greyed out).

---

## 1.7.1

**Requires:** `campaign-rpg-engine>=1.7.1`

### Initiative (turn order)

- Optional **initiative** mode: GM configures a session-wide turn order (manual add/reorder; no dice roll yet).
- Compact **initiative bar** under the map column when enabled: current actor, round, **Edit order…**, **Next ▶** (skip/advance without a turn).
- **Run turn ▶** stays manual — enabled only for the current **NPC** slot (never auto-LLM).
- Players may still **queue** compound-turn parts; **Send** is disabled until their slot (`can_act` + server 403 on `/api/player/turn`), with a clearer disabled Send state.
- Witnessed NPC compound turns group into one history card (same actor + session turn).
- Initiative state persists in session export/import (`extensions.initiative`).
- Header area actions compressed into a compact toolbar (`+` / Edit / Save… / Load… / Del).

---

## 1.7.0

**Requires:** `campaign-rpg-engine>=1.6.1`

### Player client (`/play/generic`)

- Playable player shell at `/play/generic/` with the same grid art (tokens, decorations) as the GM host.
- GM right-clicks a player agent → **Copy player join link** (short-lived seat token).
- Player API: `POST /api/seats`, `GET /api/player/view|me|assist`, `POST /api/player/turn` (Bearer seat or `?seat=`).
- View is filtered to the seated agent’s area (no hidden objects, no private LLM fields).
- Play by context menu: move / look / object interact / inventory verbs; **give** / **show** use an agent dropdown.
- Compound turns: right-click **queues** move/look/action chips under the map; **Say** / **Emote** / **Both** text dock; one **Send** commits the full turn (emote uses the action slot).
- Right-click a stacked tile opens a picker (all agents/objects on that cell), matching GM stack handling.
- Left **History** column lists each of the seated agent's compound turns as one block (step results joined), plus witnessed passive results, updated as the session advances.
- Live sync uses **Server-Sent Events** (`/api/session/stream`, `/api/player/stream`) instead of polling `/api/state` / `/api/player/view`.
- Seat token storage fails soft when the browser blocks `sessionStorage` (e.g. strict private windows).

---

## 1.6.1

**Requires:** `campaign-rpg-engine>=1.6.1`

### Prompt layout

- **Show preview** refreshes the assembled prompt and opens it in a centered modal (click outside, Close, or Escape to dismiss).
- Inline sidebar preview removed; fixed the old duplicate id that wrote prompt text into the Refresh button.

### Token budget UI

- Run turn button turns **red** when the estimate is over the hard max (yellow remains for the soft warning %).
- Context-menu **Run turn ▶** on an NPC uses the same green / yellow / red coloring (budget for that agent), including when you are currently playing as a player.
- Banner version reads `pyproject.toml` first so editable checkouts show **1.6.1** without a reinstall.

---

## 1.6.0

**Requires:** `campaign-rpg-engine>=1.6.0`

### Positioning

- Studio is the **GM host** (world/session authority), not a “reference app.” Player clients attaching later are planned, not implemented in 1.6.0.

### Hardening

- **Ruff** + GitHub Actions CI; **Biome** for `frontend/*.js`.
- FastAPI routes split into domain routers under `backend/api/`; thin `app.py`.
- Frontend: health/LLM settings carved to `frontend/api/settings.js`.
- `session_store` documented as single-session process singleton.

---

## 1.5.2

**Requires:** `campaign-rpg-engine>=1.5.2`

### Featherless + OpenRouter

- Settings gear: provider dropdown (OpenRouter | Featherless), API key, model.
- DeepSeek V4 Flash model ids differ: OpenRouter `deepseek/deepseek-v4-flash` vs Featherless `deepseek-ai/DeepSeek-V4-Flash` (documented in `.env.example`); switching provider in gear remaps that pair.
- In-memory only for this Studio process; permanent config via `.env` (see `.env.example`).

### Max input tokens

- Default hard cap **32768** estimated input tokens; turns refuse when over (engine `PromptTooLargeError`).
- Configurable **warning %** (default 90): Run turn button turns yellow at/above threshold, green below.
- Prompt API returns `over_warning` / `over_limit` / thresholds for the UI.

### Debug on failed turns

- Parse failures return `llm_response` / `prompt`; **Last response (debug)** and **Last prompt (debug)** update even when the turn fails.
- Engine repairs Featherless-style missing leading `{` on structured turns (see engine 1.5.2).

---

## 1.5.1

**Requires:** `campaign-rpg-engine>=1.5.1`

### Reference handlers — multi-step object actions

- `sequence` — run `handler_1`…`handler_3` in order (nested params use `1_` / `2_` / `3_` prefixes).
- `set_object_text` — update object `set_pdesc` / `set_desc` (`[none]` / `[empty]` to clear).
- `set_action_enabled` — show/hide an action on the current object (`target=_self` or name).
- `spawn_from_template` — spawn an entity-library object template near the actor (optional `dest-area` / `dest-at`).
- Object actions support `enabled` (Studio checkbox); disabled actions are hidden from vision and cannot be used.
- Action editor field type `template_id` — dropdown of entity templates (generic; used by spawn + inventory).

### Inventory — grant from template

- `inventory_add_from_template` — put a library object template into the actor's inventory (map-usable like pick_up; inventory plugin only).

### Turn undo

- Studio-only undo restores full session checkpoints (LLM and manual turns); Undo control in the UI.

### Prompt / vision UX (engine)

- `[far]` out-of-range object actions stay visible; `[emote]` third-person tagging; clearer unknown-interact failures with emote nudge.

---

## 1.5.0

**Requires:** `campaign-rpg-engine>=1.5.0`

### Affinity memory module

- Create-agent catalog includes built-in **`affinity`**: relationships (-10…+10) plus rolling summary (same summary interval/max/tail options as `rolling_summary`).
- Engine prompt block: Relationships → Summary → recent turns; parallel Call A/B consolidation.

### Removed: custom / uploaded memory modules

- Runtime registration (`register_memory_module_from_path` / `_from_source`), Studio upload UI, and fixture samples are **removed**.
- Memory modules are **built-in only**: ``recent_turns``, ``salient_turns``, ``rolling_summary``, ``affinity``.
- Saves referencing unknown ``module_id`` fail with a clear builtins-only error.

---

## 1.4.2

**Requires:** `campaign-rpg-engine>=1.4.2`

### Plugin fairness — schema-driven action editor + turn assist

- Handlers may declare `param_fields` + `summary_template` (engine registration / Studio `ctx.register_handler`). Catalog returns them on `GET /api/interaction-handlers`.
- Action editor and CLI builder render/emit generically from schema — **no** core `skill_check` / `move_area` / pass-fail branches in frontend.
- `register_player_turn_assist` + `GET /api/player-turn-assist`: plugins contribute `{id, label, verbs}` rows; player-turn panel filters verbs from assist (Inventory registers carried items). **Removed** `inventory_*` hardcoding from `playerTurnPanel.js`.

### Skills — pass/fail follow-up handlers

- Optional ``pass_handler`` / ``fail_handler`` on ``skill_check`` (plus ``pass_*`` / ``fail_*`` nested params), declared via `param_fields` / `handler_ref`.
- Uses engine ``run_named_handler`` after the roll; skills templates still own the spoken line (follow-ups are side effects).
- Example: DEX check → pass ``inventory_pick_up``, fail ``delete_self`` (trap).

### Action editor

- Viewport-capped modal with scrollable form and sticky Back/Save (from 1.4.1 polish).

---

## 1.4.1

**Requires:** `campaign-rpg-engine>=1.4.1`

### Skills plugin (`plugins/skills/`)

- Agent stats **CON / STR / DEX / WIS / INT / CHM** (1–20, default **10**) and named skills in `private_data` under `skills_plugin`.
- Handler **`skill_check`** — `handler_params`: `stat`, `dc`, optional `skill`, `fail_result`, `fail_passive`.
  - **Pass** → action's `result` / `passive_result`.
  - **Fail** → `ActionOutcome` from fail templates (engine 1.4.1).
- Prompt slot **`skills`** lists the active agent's stats and skills.
- Plugins panel: read-only sheet for the active agent; **Initialize stats in private_data** writes default all-10 JSON when missing. Edit values on the agent form afterward. Panel includes a JSON example (`skills`: name → level).
- Fix: editing **only** agent/object `private_data` in the Edit modal saves correctly (no longer blocked by “No changes applied” from the unrelated edit command).
- Fix: Plugins panel actions that return a snapshot (e.g. Initialize stats) refresh studio state so Edit agent shows updated `private_data` without a full page reload.

---

## 1.4.0

**Requires:** `campaign-rpg-engine>=1.4.0`

### Inventory plugin — give and show

- Turn verbs **`give`** and **`show`** — agent-to-agent carried-item actions (`target`: `"<agent_id> <item_id>"`, recipient first).
- **Range 1** (Chebyshev); auto-approach pathing toward the recipient (engine opt-in verb pathing).
- **`show`** — private detailed event to the recipient via `emit_area_event`; bystanders see passive `{actor} shows {item} to {recipient}` (recipient excluded from duplicate passive).
- Inventory prompt lists **`[give]`** **`[show]`** per carried item alongside **`[drop]`** and item actions.

### Repo hygiene

- `entity_templates/*.json` gitignored (library folder kept via `.gitkeep`).

---

## 1.3.1

**Requires:** `campaign-rpg-engine>=1.3.1`

### Area templates

- Save/load whole areas as reusable blueprints in `area_templates/` (`kind: "area"`).
- Includes grid bounds, decorations, and objects (optional toggle for hidden objects). Agents are not saved.
- REST: `POST/GET/DELETE /api/area-templates`, save-from-area, spawn (`mode: new|replace`), import/download.
- Header **Save area…** / **Load area…** buttons; Templates tab **Area templates** section.

### Assets

- Decoration uploads under `frontend/assets/` are gitignored (local only).

---

## 1.3.0

**Requires:** `campaign-rpg-engine>=1.3.0`

### Scene decorations

- Per-area **background** and **sprite** layers stored in engine snapshots (`decorations[]`, `snapshot_version` 5).
- Render stack: black viewport → background repeat → white grid → sprites by `z_index` → dashed grid lines → entity tokens.
- **Edit scene** toggle on Main tab — list panel, add/remove, move up/down, drag sprites, edit geometry.
- REST: `POST/PUT/DELETE /api/decorations`, `POST /api/decorations/reorder`.
- Decoration images under `frontend/assets/` (paths like `assets/floor.png`).

---

## 1.2.2

**Requires:** `campaign-rpg-engine>=1.2.1`

### Entity templates tab

- **Templates** tab — list, import, download, and remove library templates.
- `POST /api/entity-templates/import` — add a JSON file to the Studio library.

---

## 1.2.1

**Requires:** `campaign-rpg-engine>=1.2.1`

### Entity templates

- Save objects/agents as JSON templates under `entity_templates/` (no id or position).
- **Save as…** and **Load…** dialogs offer template library or file actions.
- Right-click empty tile → **Load…** (template library or file); right-click entity → **Save as…** (template library or file download)
- Agent save dialog: optional **Include memory** for recurring NPCs between sessions.
- API: `GET/POST/DELETE /api/entity-templates`, export/spawn-from-template, spawn at grid position with new ids.

---

## 1.2.0

**Requires:** `campaign-rpg-engine>=1.2.0`

### Plugin host

- Plugins tab — enable/disable per session, upload `.py` or `.zip` packages.
- `PluginContext` bridging handlers, turn verbs, prompt slots, events, and panel UI.
- Catalog APIs filter disabled plugin handlers, verbs, and prompt slots.

### Reference inventory plugin (`plugins/inventory/`)

- `inventory_pick_up` handler — carry objects off the map.
- `inventory_consume` handler — eat/drink carried items.
- Turn verbs: `drop` plus dynamic verbs per item action (`eat`, `drink`, …).
- Inventory prompt slot, Plugins panel (drop / use buttons).
- Grid interaction list hides `inventory_*` handlers (except pick up).

### Prompt layout

- `plugin_slot` block type in prompt editor and preview.

### Player turn panel

- Turn verb dropdown reloads when inventory changes; prefills target/verb for carried items.

---

## 1.1.1

Player turn panel on the left.

## 1.1.0

Player agents with manual compound turns; quick NPC runs.

## 1.0.1

Relative coordinate mode and agent blocking.
