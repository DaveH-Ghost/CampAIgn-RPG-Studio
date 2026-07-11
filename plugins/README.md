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

## Capabilities

| Method | Engine primitive |
|--------|------------------|
| `register_handler` | Interaction handler |
| `register_turn_verb` | Compound `action: "verb"` |
| `register_prompt_slot` | Prompt layout slot (active when enabled) |
| `on` | Session event listener (active when enabled) |
| `set_panel` / `register_panel_action` | Plugins tab UI |

## State

Store plugin data in `session.extensions[PLUGIN_ID]` (round-trips in saves).

Studio tracks enabled plugins in `session.extensions["_studio_plugins"]`.

## Examples

| Plugin | Path | What it shows |
|--------|------|----------------|
| **Inventory** | `plugins/inventory/` | Pick up, drop, consume (`inventory_consume`), prompt slot, dynamic panel |
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

## Docs

Engine primitives: [CampAIgn-RPG-Engine docs/guides/plugins.md](https://github.com/DaveH-Ghost/CampAIgn-RPG-Engine/blob/main/docs/guides/plugins.md).

New plugins should live here instead of ad-hoc `reference_handlers/` modules.
