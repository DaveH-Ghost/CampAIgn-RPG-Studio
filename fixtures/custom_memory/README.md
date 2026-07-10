# Custom memory modules

Example and contract for **runtime-loaded** memory modules. Upload via Realm-Studio **Settings → Memory modules**, or register in code with `register_memory_module_from_path`.

## Contract

Each custom module is a single `.py` file that defines:

| Symbol | Required | Purpose |
|--------|----------|---------|
| `MODULE_ID` | Yes | Unique id (must not match built-in: `recent_turns`, `salient_turns`, `rolling_summary`) |
| `create_module(**config)` | Yes | Factory returning a `MemoryModule` |
| `MODULE_LABEL` | No | Display name in create-agent UI |
| `MODULE_DESCRIPTION` | No | Short description |
| `CREATE_AGENT_OPTIONS` | No | List of `{flag, label, default, min, max?}` for create-agent UI |

The module must implement `export_state()` / `restore_state()` for session save/load (inherit from a built-in or implement on the protocol).

Import from **`realm_fabric`** in application modules.

## Example

[`rolling_summary_custom.py`](rolling_summary_custom.py) — same behavior as built-in `rolling_summary`, id `rolling_summary_custom`.

## In code

```python
from realm_fabric import register_memory_module_from_path

register_memory_module_from_path("path/to/rolling_summary_custom.py")
session.create_agent(..., memory_module="rolling_summary_custom")
```

## Save / load

Session saves reference `module_id` only (no bundled source). Before loading a save, every custom `module_id` in the save must already be registered; otherwise import fails with:

`Memory module '…' is not found. Load the module before loading this save.`
