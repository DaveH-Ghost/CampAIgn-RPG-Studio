# Reference interaction handlers

Demo handlers registered by campaign-rpg-studio at startup. **Not** part of the engine — copy this pattern in your own app.

## Layout

```
reference_handlers/
  __init__.py              # register_reference_handlers()
  handlers/
    delete_self.py
    random_move_self.py
    move_area.py
    set_object_text.py
    set_action_enabled.py
    sequence.py
    spawn_from_template.py
```

One module per handler keeps implementations easy to find and copy.

## Handlers

| `handler_id` | Params | Behavior |
|--------------|--------|----------|
| `delete_self` | — | Remove object from area |
| `random_move_self` | — | Move object to random in-bounds tile |
| `move_area` | `dest-area`, `dest-at` | Transfer interacting agent to another area |
| `spawn_from_template` | `template_id`, optional `dest-area` / `dest-at` | Spawn an object template near the actor (or at dest) |
| `set_object_text` | `set_pdesc`, `set_desc` (at least one) | Rewrite or clear (`[none]` / `[empty]`) this object's descriptions |
| `set_action_enabled` | `target` (`_self` or name), `enabled` | Show or hide an action on this object |
| `sequence` | `handler_1`…`handler_3`, nested `1_`/`2_`/`3_` params | Run several handlers in order |

### Chairs-on-table example

```text
edit-object table_1 add-action "lower chairs" range 1 handler sequence \
  handler_1 set_object_text \
  1_set_pdesc "A sturdy wooden table." \
  1_set_desc "A wooden table with chairs tucked underneath." \
  handler_2 set_action_enabled \
  2_target _self \
  2_enabled false \
  result "You lower the chairs from the tabletop." \
  passive "{actor} lowers the chairs from the table."
```

## Usage

```python
from reference_handlers import register_reference_handlers
from campaign_rpg_engine import Session, register_interaction_handler

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
