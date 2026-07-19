# CampAIgn RPG Studio



**CampAIgn RPG Studio 1.7.0** — GM host for [CampAIgn-RPG-Engine](https://github.com/DaveH-Ghost/CampAIgn-RPG-Engine) (`campaign-rpg-engine>=1.6.1`). Owns the world/session for authoring and play; players join via `/play/generic/` with a short-lived seat link.



**Distribution:** CampAIgn-RPG-Studio lives on **GitHub only** (clone and run). The engine library [`campaign-rpg-engine`](https://pypi.org/project/campaign-rpg-engine/) is installed from PyPI as a normal dependency — Studio is not published as a package.



Grid editor, multi-area sessions, lorebooks, prompt layout, session save/load, and pluggable interaction handlers. String command dispatch lives in Studio (`backend/command_dispatch.py`), not in the engine.



## Quick start



```powershell

cd path\to\CampAIgn-RPG-Studio

uv sync

copy .env.example .env   # optional; or use Settings gear in the UI

uv run campaign-rpg-studio

```



Open [http://127.0.0.1:8765](http://127.0.0.1:8765). Right-click the grid to edit; switch **Area** for multi-room sessions; **Emit event…** for GM narration; **Run turn ▶** for the active agent.

### Player client

1. Mark an agent as a **player** (create/edit agent).
2. Right-click that agent → **Copy player join link**.
3. Open the link (or [http://127.0.0.1:8765/play/generic/](http://127.0.0.1:8765/play/generic/) after pasting a `?seat=` token).
4. Right-click the grid / entities / inventory to **queue** a compound turn; edit Say/Emote under the map, then **Send**.



### Windows Smart App Control



If `uv run campaign-rpg-studio` is blocked:



```powershell

uv run python -m backend.main

```



Use `--no-browser` to skip opening the browser.



## Prerequisites



- Python ≥3.11

- [uv](https://docs.astral.sh/uv/)

- Clone this repo from GitHub (Studio is not on PyPI)

- Sibling checkout of [CampAIgn-RPG-Engine](https://github.com/DaveH-Ghost/CampAIgn-RPG-Engine) at `../CampAIgn-RPG-Engine` (editable via `[tool.uv.sources]` in `pyproject.toml`)

- **OpenRouter API key** for LLM turns (area edits work without it)



## Development layout

Clone both repos as siblings (same parent folder):

```
github/
  CampAIgn-RPG-Engine/
  CampAIgn-RPG-Studio/
```

`pyproject.toml` pins **`campaign-rpg-engine>=1.6.1`** and `[tool.uv.sources]` points at the sibling engine checkout. `uv sync` installs the engine editable — engine changes are picked up without reinstalling.

```powershell
cd CampAIgn-RPG-Studio
uv sync
uv run campaign-rpg-studio
```

### Verify against PyPI (release check)

To confirm Studio works with a published wheel only, temporarily remove the `[tool.uv.sources]` block from `pyproject.toml`, then:

```powershell
Remove-Item -Recurse -Force .venv
uv lock
uv sync
uv run pytest
```

Restore `[tool.uv.sources]` for day-to-day co-development.



## Features



- **Grid** — pannable multi-area map; footprints, blocking, hidden objects, triggers

- **Entities** — create/edit agents and objects; player agents with manual turns

- **Lorebooks** — SillyTavern JSON import; keyword scan into prompts

- **Entity templates** — save/load from the grid; **Templates** tab for library management

- **Plugins** — capability-based plugin host (`plugins/` folder + upload); enable per session; see [`plugins/README.md`](plugins/README.md)

- **Prompt layout** — reorder blocks, slot settings, lorebook injection

- **Settings** — in-memory LLM key/model

- **Session** — export/import full save JSON



## Reference handlers



Demo interaction handlers (`delete_self`, `random_move_self`, `move_area`, `sequence`, `set_object_text`, `set_action_enabled`, `spawn_from_template`) live in [`reference_handlers/`](reference_handlers/). They are **Studio-owned sample handlers**, not part of the engine — copy this pattern in your own projects.

For new extensions, prefer the [**Plugins**](plugins/README.md) tab and `plugins/` packages (handlers, turn verbs, prompt slots, events, panel UI).



Custom plugins sample: [`plugins/`](plugins/) (Plugins tab). Built-in memory modules are selected when creating an agent (no custom memory upload).



## Tests



```powershell

uv run pytest

```



HTTP integration tests via FastAPI `TestClient` (mocked LLM — no API key required).



## Environment



| Variable | Required | Description |

|----------|----------|-------------|

| `OPENROUTER_API_KEY` | For **Run turn** | [OpenRouter](https://openrouter.ai/) API key |

| `OPENROUTER_MODEL` | No | Default: `deepseek/deepseek-v4-flash` |



Settings gear overrides these in memory until server restart.



## Troubleshooting



If `uv sync` fails with **Access is denied** on `campaign-rpg-studio.exe`, stop the running server (Ctrl+C in the terminal where `uv run campaign-rpg-studio` is active), then:



```powershell

Remove-Item -Recurse -Force .venv

uv sync

```



## License



MIT — see [LICENSE](LICENSE).

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

