"""campaign-rpg-studio FastAPI application.

Routes live in domain routers under ``backend/api``. ``create_app`` stays thin:
build the app, configure CORS, register routers, mount the frontend, and serve
the index page.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from backend.api import register_routers
from backend.frontend_assets import render_index_html
from backend.plugin_upload import load_all_plugins
from backend.version import studio_version

_STUDIO_DIR = Path(__file__).resolve().parent.parent
_FRONTEND_DIR = _STUDIO_DIR / "frontend"
_PLAY_GENERIC_DIR = _STUDIO_DIR / "play" / "generic"
# Sibling engine checkout (co-dev); optional for uvicorn reload.
_ENGINE_ROOT = _STUDIO_DIR.parent / "CampAIgn-RPG-Engine"


def _ensure_reference_handlers() -> None:
    from reference_handlers import register_reference_handlers

    register_reference_handlers()


@asynccontextmanager
async def _app_lifespan(_app: FastAPI):
    from backend.concurrency_bridge import register_concurrency_limit_bridge

    _ensure_reference_handlers()
    load_all_plugins()
    register_concurrency_limit_bridge()
    yield


def create_app() -> FastAPI:
    from backend.concurrency_bridge import register_concurrency_limit_bridge

    _ensure_reference_handlers()
    load_all_plugins()
    register_concurrency_limit_bridge()
    app = FastAPI(title="campaign-rpg-studio", version=studio_version(), lifespan=_app_lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:8765",
            "http://localhost:8765",
            "http://127.0.0.1:5173",
            "http://localhost:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def publish_api_mutations(request, call_next):
        response = await call_next(request)
        path = request.url.path
        if (
            request.method in {"POST", "PUT", "PATCH", "DELETE"}
            and path.startswith("/api/")
            and "/stream" not in path
            and response.status_code < 400
        ):
            from backend.session_events import publish_session_changed

            publish_session_changed()
        return response

    register_routers(app)

    _NO_STORE = {
        "Cache-Control": "no-store, no-cache, must-revalidate",
        "Pragma": "no-cache",
    }

    @app.middleware("http")
    async def frontend_cache_headers(request, call_next):
        """Never let browsers keep stale Studio/play shells or modules."""
        response = await call_next(request)
        path = request.url.path
        if path == "/" or path.endswith(".html"):
            response.headers.update(_NO_STORE)
        elif path.endswith((".js", ".mjs", ".css")) and (
            path.startswith("/static/") or path.startswith("/play/generic/assets/")
        ):
            # no-store: Firefox module cache ignores weaker no-cache in private windows.
            response.headers["Cache-Control"] = "no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
        return response

    @app.get("/")
    def index() -> HTMLResponse:
        return HTMLResponse(render_index_html(), headers=dict(_NO_STORE))

    @app.get("/play/generic")
    @app.get("/play/generic/")
    def play_generic_index() -> FileResponse:
        return FileResponse(
            _PLAY_GENERIC_DIR / "index.html",
            headers=dict(_NO_STORE),
        )

    if _FRONTEND_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=_FRONTEND_DIR), name="static")
    if _PLAY_GENERIC_DIR.is_dir():
        app.mount(
            "/play/generic/assets",
            StaticFiles(directory=_PLAY_GENERIC_DIR),
            name="play_generic",
        )

    return app


app = create_app()

_DEFAULT_HOST = "127.0.0.1"
_DEFAULT_PORT = 8765
_DEFAULT_URL = f"http://{_DEFAULT_HOST}:{_DEFAULT_PORT}"


def main() -> None:
    import argparse
    import threading
    import webbrowser

    import uvicorn

    parser = argparse.ArgumentParser(prog="campaign-rpg-studio")
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open the default browser on startup",
    )
    args = parser.parse_args()

    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(_DEFAULT_URL)).start()

    reload_dirs = [str(_STUDIO_DIR)]
    if _ENGINE_ROOT.is_dir():
        reload_dirs.append(str(_ENGINE_ROOT))

    uvicorn.run(
        "backend.app:app",
        host=_DEFAULT_HOST,
        port=_DEFAULT_PORT,
        reload=True,
        reload_dirs=reload_dirs,
        reload_excludes=[".custom_plugins/*"],
    )


if __name__ == "__main__":
    main()
