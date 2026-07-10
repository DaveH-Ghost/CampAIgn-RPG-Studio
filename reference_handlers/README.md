# Reference interaction handlers

Demo handlers registered by realm-studio at startup. **Not** part of the engine — copy this pattern in your own app.

## Layout

```
reference_handlers/
  __init__.py              # register_reference_handlers()
  handlers/
    delete_self.py
    random_move_self.py
    move_area.py
```

One module per handler keeps implementations easy to find and copy.

## Handlers

| `handler_id` | Params | Behavior |
|--------------|--------|----------|
| `delete_self` | — | Remove object from area |
| `random_move_self` | — | Move object to random in-bounds tile |
| `move_area` | `dest-area`, `dest-at` | Transfer interacting agent to another area |

## Usage

```python
from reference_handlers import register_reference_handlers
from realm_fabric import Session, register_interaction_handler

register_reference_handlers()

# Or register your own:
def eat_food(session, area, agent, obj, action):
    area.remove_object(obj.id)
    return None

register_interaction_handler("eat_food", eat_food, description="Remove object (eaten)")
```

Object actions reference handlers via CLI:

```text
create-object ... action eat range 1 handler delete_self result "..." passive "..."
```

Saves with `handler_id` require the same handlers to be registered before `import-session` or `Session.from_snapshot`.
