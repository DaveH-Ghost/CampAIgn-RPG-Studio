# CampAIgn RPG Studio



Reference GM web app for [CampAIgn-RPG-Engine](https://github.com/DaveH-Ghost/CampAIgn-RPG-Engine) **1.0** — a fully functional example of building on the `campaign-rpg-engine` Python library.



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

- **`campaign-rpg-engine`** engine from PyPI (`campaign-rpg-engine>=1.0.0` in `pyproject.toml`)

- **OpenRouter API key** for LLM turns (area edits work without it)



## Co-developing with a local engine checkout

`pyproject.toml` pins **`campaign-rpg-engine>=1.0.0` from PyPI**. To hack on unreleased engine changes on the same machine:

```powershell
cd CampAIgn-RPG-Studio
uv sync
uv pip install -e ..\CampAIgn-RPG-Engine
uv run campaign-rpg-studio
```

That editable install overrides PyPI in your local `.venv` only — nothing to commit.



## Features



- **Grid** — pannable multi-area map; footprints, blocking, hidden objects, triggers

- **Entities** — create/edit agents and objects; player agents with manual turns

- **Lorebooks** — SillyTavern JSON import; keyword scan into prompts

- **Prompt layout** — reorder blocks, slot settings, lorebook injection

- **Settings** — in-memory LLM key/model; custom memory module upload

- **Session** — export/import full save JSON



## Reference handlers



Demo interaction handlers (`delete_self`, `random_move_self`, `move_area`) live in [`reference_handlers/`](reference_handlers/). They are **app-owned**, not part of the engine — copy this pattern in your own projects.



Custom memory module sample and upload UI: [`fixtures/custom_memory/`](fixtures/custom_memory/) (Settings → Memory modules).



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

