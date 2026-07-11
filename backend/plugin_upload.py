"""Discover and load Studio plugins from disk (1.2.0)."""

from __future__ import annotations

import importlib.util
import io
import sys
import zipfile
from pathlib import Path
from typing import Any

from backend.plugin_context import PluginContext, PluginManifest
from backend.plugin_registry import get_plugin_manifest, register_plugin_manifest

_STUDIO_DIR = Path(__file__).resolve().parent.parent
PLUGINS_DIR = _STUDIO_DIR / "plugins"
CUSTOM_PLUGINS_DIR = _STUDIO_DIR / ".custom_plugins"


def _load_module_from_path(module_path: Path, module_name: str) -> Any:
    if not module_path.is_file():
        raise ValueError(f"Plugin module not found: {module_path}")
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Could not load plugin from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _parse_plugin_module(module: Any, *, source_path: str) -> PluginManifest:
    plugin_id = getattr(module, "PLUGIN_ID", None)
    if not plugin_id or not isinstance(plugin_id, str):
        raise ValueError('Plugin must define PLUGIN_ID = "your_plugin_id"')
    plugin_id = plugin_id.strip()
    label = str(getattr(module, "PLUGIN_LABEL", plugin_id.replace("_", " ").title()))
    version = str(getattr(module, "PLUGIN_VERSION", "1"))
    register_fn = getattr(module, "register", None)
    if register_fn is None or not callable(register_fn):
        raise ValueError(f"Plugin {plugin_id} must define register(ctx)")

    manifest = PluginManifest(
        plugin_id=plugin_id,
        label=label,
        version=version,
        description=str(getattr(module, "PLUGIN_DESCRIPTION", "")),
        source_path=source_path,
    )
    ctx = PluginContext(manifest)
    result = register_fn(ctx)
    if isinstance(result, PluginManifest):
        manifest = result
    elif isinstance(result, dict):
        for key, value in result.items():
            if hasattr(manifest, key):
                setattr(manifest, key, value)
    return manifest


def load_plugin_from_directory(plugin_dir: Path) -> str:
    init_py = plugin_dir / "__init__.py"
    module = _load_module_from_path(
        init_py,
        f"studio_plugin_{plugin_dir.name}",
    )
    manifest = _parse_plugin_module(module, source_path=str(plugin_dir.resolve()))
    if get_plugin_manifest(manifest.plugin_id) is not None:
        return manifest.plugin_id
    register_plugin_manifest(manifest)
    return manifest.plugin_id


def load_plugin_from_file(plugin_file: Path) -> str:
    module = _load_module_from_path(
        plugin_file,
        f"studio_plugin_{plugin_file.stem}",
    )
    manifest = _parse_plugin_module(module, source_path=str(plugin_file.resolve()))
    if get_plugin_manifest(manifest.plugin_id) is not None:
        return manifest.plugin_id
    register_plugin_manifest(manifest)
    return manifest.plugin_id


def _discover_plugin_dirs(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    dirs: list[Path] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir() or child.name.startswith("_"):
            continue
        if (child / "__init__.py").is_file():
            dirs.append(child)
    return dirs


def load_all_plugins(*, extra_dirs: list[Path] | None = None) -> list[str]:
    """Load plugins from ``plugins/``, ``.custom_plugins/``, and optional *extra_dirs*."""
    loaded: list[str] = []
    roots = [PLUGINS_DIR, CUSTOM_PLUGINS_DIR]
    if extra_dirs:
        roots.extend(extra_dirs)
    for root in roots:
        for plugin_dir in _discover_plugin_dirs(root):
            try:
                plugin_id = load_plugin_from_directory(plugin_dir)
            except (OSError, ValueError, TypeError):
                continue
            if plugin_id not in loaded:
                loaded.append(plugin_id)
        if root == CUSTOM_PLUGINS_DIR:
            for plugin_file in sorted(root.glob("*.py")):
                if plugin_file.name.startswith("_"):
                    continue
                try:
                    plugin_id = load_plugin_from_file(plugin_file)
                except (OSError, ValueError, TypeError):
                    continue
                if plugin_id not in loaded:
                    loaded.append(plugin_id)
    return loaded


def upload_plugin(*, source: str | bytes, filename: str) -> dict[str, Any]:
    """Install an uploaded plugin (.py or .zip package) into ``.custom_plugins/``."""
    CUSTOM_PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
    name = Path(filename).name
    lower = name.lower()

    if lower.endswith(".zip"):
        data = source if isinstance(source, bytes) else source.encode("utf-8")
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            zf.extractall(CUSTOM_PLUGINS_DIR)
        plugin_id = ""
        for plugin_dir in _discover_plugin_dirs(CUSTOM_PLUGINS_DIR):
            try:
                plugin_id = load_plugin_from_directory(plugin_dir)
            except (OSError, ValueError, TypeError):
                continue
            break
        return {
            "ok": True,
            "plugin_id": plugin_id or None,
            "message": f"Uploaded plugin archive {name!r}.",
        }

    if not lower.endswith(".py"):
        raise ValueError("Plugin upload must be a .py file or .zip package.")
    text = source if isinstance(source, str) else source.decode("utf-8")
    dest = CUSTOM_PLUGINS_DIR / name
    dest.write_text(text, encoding="utf-8")
    plugin_id = load_plugin_from_file(dest)
    return {
        "ok": True,
        "plugin_id": plugin_id,
        "message": f"Loaded plugin {plugin_id!r}.",
    }
