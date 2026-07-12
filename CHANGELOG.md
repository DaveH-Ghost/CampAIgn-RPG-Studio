# Changelog — CampAIgn-RPG-Studio

Studio is distributed via GitHub only (not PyPI). Version tags match `pyproject.toml`.

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
