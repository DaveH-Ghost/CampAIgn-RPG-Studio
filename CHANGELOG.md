# Changelog — CampAIgn-RPG-Studio

Studio is distributed via GitHub only (not PyPI). Version tags match `pyproject.toml`.

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
