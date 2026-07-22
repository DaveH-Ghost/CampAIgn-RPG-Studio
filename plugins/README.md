# CampAIgn-RPG-Studio plugins

Third-party plugins extend CampAIgn via a single `register(ctx)` entry point.

## Layout

```
plugins/
  my_plugin/
    __init__.py    # PLUGIN_ID, register(ctx)
```

Uploaded plugins are cached under `.custom_plugins/` (survives dev reload).

## Contract

```python
PLUGIN_ID = "my_plugin"
PLUGIN_LABEL = "My Plugin"
PLUGIN_VERSION = "1"
PLUGIN_DESCRIPTION = "Optional description"

def register(ctx):
    ctx.register_handler("my_handler", my_fn, description="...")
    ctx.register_turn_verb("use", my_verb_fn, description="...")
    ctx.register_prompt_slot("my_plugin", my_slot_renderer, description="...")
    ctx.register_player_turn_assist(my_assist_builder)
    ctx.on("turn_committed", my_listener)
    ctx.set_panel({
        "title": "My Plugin",
        "sections": [
            {"type": "text", "content": "Hello."},
            {"type": "button", "id": "ping", "label": "Ping"},
        ],
    })
    ctx.register_panel_action("ping", lambda session, params: {"ok": True, "message": "pong"})
```

`register_handler` may also pass **`param_fields`** (list of field dicts) and **`summary_template`** (e.g. `"skill_check {stat} DC {dc}"`) so the Studio action editor renders params and manage-list summaries without frontend patches. Field `type` values: `text`, `textarea`, `number`, `select`, `area_id`, `template_id` (entity template library; optional `kind: "object"|"agent"` filter), `coord`, `handler_ref` (nested handler pick with `param_prefix` / `exclude_handlers`).

`register_player_turn_assist(builder)` — `builder(session)` returns `[{id, label, verbs: [str]}, ...]`. Host merges enabled plugins on `GET /api/player-turn-assist` for the player-turn verb/target UI.

`register_entity_form_section(kind, section_id, builder, private_key=..., apply_values=...)` — adds fields under create/edit **Plugins** (object or agent). Host merges via `GET /api/entity-form-sections` and `POST /api/entity-form-sections/merge`.

## Capabilities

| Method | Engine primitive |
|--------|------------------|
| `register_handler` | Interaction handler (+ optional `param_fields` / `summary_template` for Studio UI) |
| `register_turn_verb` | Compound `action: "verb"` |
| `register_prompt_slot` | Prompt layout slot (active when enabled) |
| `register_interact_template_vars` | Extra `{name}` entries in action-editor `?` help (when enabled); handlers must substitute them |
| `register_player_turn_assist` | Verb/target rows for Studio player-turn panel (when enabled) |
| `register_entity_form_section` | Create/edit modal Plugins fields → `private_data` merge |
| `on` | Session event listener (active when enabled) |
| `set_panel` / `register_panel_action` | Plugins tab UI |

## State

Store plugin data in `session.extensions[PLUGIN_ID]` (round-trips in saves).

Studio tracks enabled plugins in `session.extensions["_studio_plugins"]`.

## Examples

| Plugin | Path | What it shows |
|--------|------|----------------|
| **Inventory** | `plugins/inventory/` | Pick up, drop, give/show, consume, prompt slot, dynamic panel |
| **Skills** | `plugins/skills/` | Stats/skills in `private_data`, `skill_check` handler, prompt slot, panel |
| **Combat** | `plugins/combat/` | HP/AC, equip, attacks (needs initiative); soft-requires Inventory + Skills |
| Hello (tests only) | `tests/fixtures/plugins/hello_plugin/` | Minimal enable/disable, static panel, events |

### Inventory setup

1. Enable **Inventory** on the Plugins tab.
2. On an object, add action `pick_up` with handler `inventory_pick_up` (range 1+).
3. Interact with `pick_up` to store the object off the map.
4. For consumables, add an interact action (e.g. `drink`) with handler `inventory_consume`.
5. Drop from the Plugins panel or turn `action: "verb"`, `verb: "drop"`, `target: <item id>`.
6. Use carried items with `action: "verb"`, `verb: <action name>`, `target: <item id>` (e.g. `drink`).

Handlers whose id starts with `inventory_` (except `inventory_pick_up`) are **inventory-only** — hidden from map interaction lists and only usable while carried.

Carried items live in `session.extensions["inventory"]` and round-trip in session export/import.

### Skills setup

1. Enable **Skills** on the Plugins tab.
2. On a new agent, open the Skills panel and click **Initialize stats in private_data** (writes default all-10 stats). Then edit via right-click → **Edit** → Advanced → **private_data**, e.g.:

```json
{
  "skills_plugin": {
    "stats": { "CON": 10, "STR": 12, "DEX": 14, "WIS": 8, "INT": 16, "CHM": 11 },
    "skills": { "lockpicking": 3 }
  }
}
```

Missing stats default to **10**. Modifier is `(score - 10) // 2`. The Plugins panel shows the active agent's sheet (read-only) plus a JSON example.

Skills format — string name to integer level:

```json
"skills": { "lockpicking": 3, "persuasion": 1 }
```

3. On an object action, set handler `skill_check` with params:
   - `stat` (required): `CON`/`STR`/`DEX`/`WIS`/`INT`/`CHM`
   - `dc` (required): difficulty number
   - `skill` (optional): skill name; bonus = skill level if present
   - `fail_result` / `fail_passive` (optional): fail templates (`{actor}`, `{object}` ok)
   - `pass_handler` / `fail_handler` (optional): other handler ids to run after pass/fail
     (nested params as `pass_dest-area`, `fail_dest-at`, …). Cannot nest `skill_check`.
4. On a **pass**, the action's usual `result` / `passive_result` fire. On a **fail**, fail templates are used instead. Both support skills placeholders `{raw_roll}`, `{roll_bonus}`, `{modified_roll}`, `{dc_target}` (amber in the `?` help while Skills is enabled). Follow-up handlers run for side effects; skills keeps the narrative line.

Add a Prompt layout block `plugin_slot` named `skills` so agents see their sheet.

### Combat setup

1. Enable **Inventory**, **Skills**, and **Combat** on the Plugins tab.
2. Put fighters in the **initiative** order, then **Start combat** (or emit `[Combat Start] …`). Start refuses if initiative is off/empty.
3. Create/edit an object → **Plugins → Combat**: set Weapon or Armor **stats** only (range, attack stat, damage, AC, …). Attack verb names are not set here.
4. **Manage actions**: add one or more actions (e.g. `swing`, `slash`, `shoot`) with handler **`combat_attack`**. Same weapon stats apply to all of them; hit text = action result/passive; miss text = `miss_result` / `miss_passive`. Amber placeholders: `{attack_roll}`, `{attack_bonus}`, `{attack_total}`, `{target_ac}`, `{attack_detail}`, `{damage_detail}`, `{damage_total}`, `{target_hp}`, `{target}`, `{action}`, `{weapon}`.
5. Grant gear: Inventory panel → pick an object template → **Add to inventory**. Equip with verb `equip` / `unequip`.
6. Combat panel → set active agent **max HP** (fills current HP). In combat, use a Manage-action attack name on the equipped weapon (or `unarmed`) with `target` = foe agent id.
7. Add a Prompt layout block `plugin_slot` named `combat` **below** inventory.

HP defaults to **10** when combat starts if missing. HP ≤ 0 downs the agent (removed from initiative). No spectator turns in v1 — only agents on the initiative list act during combat.

## Docs

Engine primitives: [CampAIgn-RPG-Engine docs/guides/plugins.md](https://github.com/DaveH-Ghost/CampAIgn-RPG-Engine/blob/main/docs/guides/plugins.md).

New plugins should live here instead of ad-hoc `reference_handlers/` modules.
