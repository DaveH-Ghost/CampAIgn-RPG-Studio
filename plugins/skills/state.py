"""Skills plugin enablement and private_data key."""

from __future__ import annotations

PLUGIN_ID = "skills"
_STUDIO_PLUGINS_KEY = "_studio_plugins"
PRIVATE_KEY = "skills_plugin"


def plugin_enabled(session) -> bool:
    raw = session.extensions.get(_STUDIO_PLUGINS_KEY) or {}
    enabled = raw.get("enabled") or []
    return PLUGIN_ID in enabled
