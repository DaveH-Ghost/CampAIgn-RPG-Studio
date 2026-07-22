"""Studio frontend cache-busting helpers.

Firefox (and other browsers) cache ES modules by URL for the life of a session,
including private windows. Versioned URLs + import maps keep every module in sync
when any static file changes — without hand-editing ``?v=`` on each import.
"""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path

from backend.version import studio_version

_STUDIO_DIR = Path(__file__).resolve().parent.parent
_FRONTEND_DIR = _STUDIO_DIR / "frontend"


def _fingerprint_frontend() -> str:
    """Stable short hash of all frontend file mtimes/sizes (and paths)."""
    digest = hashlib.sha256()
    if not _FRONTEND_DIR.is_dir():
        return "missing"
    paths = sorted(
        p
        for p in _FRONTEND_DIR.rglob("*")
        if p.is_file() and p.suffix.lower() in {".js", ".css", ".html", ".svg", ".png", ".webp"}
    )
    for path in paths:
        rel = path.relative_to(_FRONTEND_DIR).as_posix()
        stat = path.stat()
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(stat.st_mtime_ns).encode("ascii"))
        digest.update(b"\0")
        digest.update(str(stat.st_size).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()[:12]


@lru_cache(maxsize=1)
def _cached_revision(fingerprint: str) -> str:
    return f"{studio_version()}-{fingerprint}"


def asset_revision() -> str:
    """Return a revision string that changes whenever frontend assets change."""
    return _cached_revision(_fingerprint_frontend())


def clear_asset_revision_cache() -> None:
    _cached_revision.cache_clear()


def iter_frontend_js() -> list[Path]:
    if not _FRONTEND_DIR.is_dir():
        return []
    return sorted(p for p in _FRONTEND_DIR.rglob("*.js") if p.is_file())


def import_map_json(rev: str | None = None) -> str:
    """JSON for ``<script type="importmap">`` remapping ``/static/*.js`` → versioned URLs."""
    rev = rev or asset_revision()
    imports: dict[str, str] = {}
    for path in iter_frontend_js():
        rel = path.relative_to(_FRONTEND_DIR).as_posix()
        url = f"/static/{rel}"
        imports[url] = f"{url}?v={rev}"
    return json.dumps({"imports": imports}, indent=2)


def render_index_html() -> str:
    """Load index.html and inject import map + asset revision query params."""
    rev = asset_revision()
    raw = (_FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
    import_map = (
        f'<script type="importmap">\n{import_map_json(rev)}\n</script>\n'
    )
    if "<!-- IMPORT_MAP -->" in raw:
        html = raw.replace("<!-- IMPORT_MAP -->", import_map, 1)
    else:
        html = raw.replace("<head>", f"<head>\n  {import_map}", 1)
    return html.replace("{{ASSET_REV}}", rev)