"""Plugin host context bridging Studio plugins to engine registries (1.2.0)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from campaign_rpg_engine import (
    register_event_listener,
    register_interaction_handler,
    register_prompt_slot,
    register_turn_verb,
)

EventListener = Callable[..., None]


@dataclass
class PluginManifest:
    plugin_id: str
    label: str
    version: str = "1"
    description: str = ""
    source_path: str = ""
    panel: dict[str, Any] = field(default_factory=dict)
    panel_builder: Callable[[Any], dict[str, Any]] | None = None
    event_listeners: list[tuple[str, EventListener]] = field(default_factory=list)
    prompt_slots: list[tuple[str, Any, str]] = field(default_factory=list)
    handler_ids: list[str] = field(default_factory=list)
    turn_verb_ids: list[str] = field(default_factory=list)
    panel_actions: dict[str, Callable[..., dict[str, Any]]] = field(default_factory=dict)

    def to_catalog_dict(self, *, enabled: bool) -> dict[str, Any]:
        return {
            "id": self.plugin_id,
            "label": self.label,
            "version": self.version,
            "description": self.description,
            "enabled": enabled,
            "source_path": self.source_path,
        }


_STUDIO_PLUGINS_KEY = "_studio_plugins"


def _plugin_enabled(session, plugin_id: str) -> bool:
    raw = session.extensions.get(_STUDIO_PLUGINS_KEY) or {}
    enabled = raw.get("enabled") or []
    return plugin_id in enabled


class PluginContext:
    """Capability surface passed to ``register(ctx)``."""

    def __init__(self, manifest: PluginManifest) -> None:
        self._manifest = manifest

    @property
    def plugin_id(self) -> str:
        return self._manifest.plugin_id

    def on(self, event: str, listener: EventListener) -> None:
        self._manifest.event_listeners.append((event.strip(), listener))

    def register_handler(
        self,
        handler_id: str,
        handler: Callable,
        *,
        description: str = "",
        validate_params: Callable | None = None,
    ) -> None:
        cleaned = handler_id.strip()
        register_interaction_handler(
            cleaned,
            handler,
            description=description,
            validate_params=validate_params,
        )
        if cleaned and cleaned not in self._manifest.handler_ids:
            self._manifest.handler_ids.append(cleaned)

    def register_turn_verb(
        self,
        verb_id: str,
        executor: Callable,
        *,
        description: str = "",
        validate_turn: Callable | None = None,
    ) -> None:
        cleaned = verb_id.strip()
        register_turn_verb(
            cleaned,
            executor,
            description=description,
            validate_turn=validate_turn,
        )
        if cleaned and cleaned not in self._manifest.turn_verb_ids:
            self._manifest.turn_verb_ids.append(cleaned)

    def register_prompt_slot(
        self,
        name: str,
        renderer: Callable,
        *,
        description: str = "",
    ) -> None:
        slot_name = name.strip()
        self._manifest.prompt_slots.append((slot_name, renderer, description))
        plugin_id = self.plugin_id

        def wrapped(session, agent, area, ctx, options):
            if not _plugin_enabled(session, plugin_id):
                return ""
            return renderer(session, agent, area, ctx, options)

        register_prompt_slot(slot_name, wrapped, description=description)

    def set_panel(self, panel: dict[str, Any]) -> None:
        self._manifest.panel = dict(panel)

    def set_panel_builder(self, builder: Callable[[Any], dict[str, Any]]) -> None:
        """Build the Plugins tab panel from live session state when fetched."""
        self._manifest.panel_builder = builder

    def register_panel_action(
        self,
        action_id: str,
        handler: Callable[..., dict[str, Any]],
    ) -> None:
        self._manifest.panel_actions[action_id.strip()] = handler
