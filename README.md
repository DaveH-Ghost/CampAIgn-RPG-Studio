# realm-studio



Reference GM web app for [Realm-Fabric](https://github.com/DaveH-Ghost/Realm-Fabric) **1.0** — a fully functional example of building on the `realm-fabric` Python library.



**Distribution:** Realm-Studio lives on **GitHub only** (clone and run). The engine library [`realm-fabric`](https://pypi.org/project/realm-fabric/) is installed from PyPI as a normal dependency — Studio is not published as a package.



Grid editor, multi-area sessions, lorebooks, prompt layout, session save/load, and pluggable interaction handlers. String command dispatch lives in Studio (`backend/command_dispatch.py`), not in the engine.



## Quick start



```powershell

cd path\to\Realm-Studio

uv sync

copy .env.example .env   # optional; or use Settings gear in the UI

uv run realm-studio

```



Open [http://127.0.0.1:8765](http://127.0.0.1:8765). Right-click the grid to edit; switch **Area** for multi-room sessions; **Emit event…** for GM narration; **Run turn ▶** for the active agent.



### Windows Smart App Control



If `uv run realm-studio` is blocked:



```powershell

uv run python -m backend.main

```



Use `--no-browser` to skip opening the browser.



## Prerequisites



- Python ≥3.11

- [uv](https://docs.astral.sh/uv/)

- Clone this repo from GitHub (Studio is not on PyPI)

- **`realm-fabric`** engine from PyPI (`realm-fabric>=1.0.0` in `pyproject.toml`)

- **OpenRouter API key** for LLM turns (area edits work without it)



## Co-developing with a local engine checkout

`pyproject.toml` pins **`realm-fabric>=1.0.0` from PyPI**. To work on unreleased engine changes on the same machine:

```powershell
cd Realm-Studio
uv sync
uv pip install -e ..\Realm-Fabric
uv run realm-studio
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



If `uv sync` fails with **Access is denied** on `realm-studio.exe`, stop the running server (Ctrl+C in the terminal where `uv run realm-studio` is active), then:



```powershell

Remove-Item -Recurse -Force .venv

uv sync

```



## License



MIT — see [LICENSE](LICENSE).

