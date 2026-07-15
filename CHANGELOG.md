# Changelog — CampAIgn-RPG-Studio

Studio is distributed via GitHub only (not PyPI). Version tags match `pyproject.toml`.

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
