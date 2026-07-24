# CampAIgn RPG Studio



**CampAIgn RPG Studio 1.7.5** — GM host for [CampAIgn-RPG-Engine](https://github.com/DaveH-Ghost/CampAIgn-RPG-Engine) (`campaign-rpg-engine>=1.7.4`). Owns the world/session for authoring and play; players join via `/play/generic/` with a short-lived seat link.



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
4. Right-click the grid / entities / inventory to **queue** a compound turn; edit Say/Emote under the map, then **Send** (when initiative is on, Send is only active on your slot).

### Remote host (droplet / VPS)

By default Studio listens on **`127.0.0.1:8765`** (local testing only). To let friends join from the internet:

1. On the server, start Studio bound to all interfaces (and skip opening a local browser):

```bash
uv run campaign-rpg-studio --host 0.0.0.0 --no-browser
```

Or set env (see `.env.example`):

```bash
export CAMPAIGN_STUDIO_HOST=0.0.0.0
export CAMPAIGN_STUDIO_PORT=8765
uv run campaign-rpg-studio --no-browser
```

2. Open the **firewall** for that port (or put **nginx/Caddy** in front with HTTPS).
3. As GM, open Studio in your browser using the **public** address (`http://YOUR_DROPLET_IP:8765` or `https://your.domain`).
4. Optional but recommended behind a reverse proxy: **Settings → Hosting / player links → Public base URL** (e.g. `https://your.domain`), or set `CAMPAIGN_STUDIO_PUBLIC_URL`. Join links then use that host instead of whatever is in the request.
5. Right-click a player agent → **Copy player join link** → send that URL. Seats expire after about an hour (in-memory; restarting Studio invalidates them).

Notes:

- One Studio process is still **one session** (GM host). This is remote co-op, not a multi-room lobby.
- Keep API keys on the server; players only need the join link.
- Prefer HTTPS in production so seat tokens are not sent over plain HTTP.

### Initiative (1.7.1)

On the GM **Main** tab, use **Configure…** on the initiative bar to enable turn order, add any session agents, and reorder. **Run turn ▶** runs the LLM only for the current NPC; players act from `/play/generic` when it is their turn.



### Windows Smart App Control



If `uv run campaign-rpg-studio` is blocked:



```powershell

uv run python -m backend.main

```



Use `--no-browser` to skip opening the browser. Use `--host 0.0.0.0` (or `CAMPAIGN_STUDIO_HOST`) for remote players — see **Remote host** above.



## Prerequisites



- Python ≥3.11

- [uv](https://docs.astral.sh/uv/)

- Clone this repo from GitHub (Studio is not on PyPI)

- Python package [`campaign-rpg-engine`](https://pypi.org/project/campaign-rpg-engine/) from PyPI (`>=1.7.4`) — installed by `uv sync`

- **OpenRouter API key** for LLM turns (area edits work without it)



## Development layout

`uv sync` installs **`campaign-rpg-engine` from PyPI** by default.

```powershell
cd CampAIgn-RPG-Studio
uv sync
uv run campaign-rpg-studio
```

### Sibling engine (co-development)

To edit the engine and Studio together, clone both as siblings and uncomment `[tool.uv.sources]` in `pyproject.toml`:

```
github/
  CampAIgn-RPG-Engine/
  CampAIgn-RPG-Studio/
```

```toml
[tool.uv.sources]
campaign-rpg-engine = { path = "../CampAIgn-RPG-Engine", editable = true }
```

Then `uv sync` again (do not commit that uncomment unless you intend to). Engine changes apply without reinstalling.



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
| `OPENROUTER_API_KEY` | For **Run turn** (or Featherless key) | [OpenRouter](https://openrouter.ai/) API key |
| `OPENROUTER_MODEL` | No | Default: `deepseek/deepseek-v4-flash` |
| `FEATHERLESS_API_KEY` | Alt for **Run turn** | Featherless API key when `LLM_PROVIDER=featherless` |
| `FEATHERLESS_MODEL` | No | Default: `deepseek-ai/DeepSeek-V4-Flash` |
| `LLM_PROVIDER` | No | `openrouter` (default) or `featherless` |
| `CAMPAIGN_STUDIO_HOST` | No | Bind address; default `127.0.0.1`. Use `0.0.0.0` for remote players |
| `CAMPAIGN_STUDIO_PORT` | No | Bind port; default `8765` |
| `CAMPAIGN_STUDIO_PUBLIC_URL` | No | Public origin for player join links (e.g. `https://your.domain`) |

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

