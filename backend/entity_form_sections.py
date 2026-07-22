"""Entity create/edit form sections contributed by Studio plugins."""

from __future__ import annotations

import json
from typing import Any

from backend.plugin_registry import is_plugin_enabled, list_installed_plugins


def _parse_private_dict(text: str) -> tuple[dict[str, Any] | None, str | None]:
    cleaned = (text or "").strip()
    if not cleaned:
        return {}, None
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return None, "private_data must be JSON to merge plugin form sections."
    if not isinstance(data, dict):
        return None, "private_data JSON must be an object."
    return data, None


def field_prefix(plugin_id: str, section_id: str) -> str:
    return f"efs_{plugin_id}_{section_id}_"


def merged_entity_form_sections(
    session,
    kind: str,
    *,
    entity_id: str | None = None,
) -> dict[str, Any]:
    """Return enabled plugin form sections for *kind* (object|agent)."""
    cleaned_kind = (kind or "").strip().lower()
    if cleaned_kind not in ("object", "agent"):
        return {"ok": False, "message": "kind must be 'object' or 'agent'."}

    entity = None
    if entity_id:
        entity = session.get_agent(entity_id)
        if entity is None:
            located = session.find_object(entity_id)
            if located is not None:
                entity = located[1]

    sections: list[dict[str, Any]] = []
    for manifest in list_installed_plugins():
        if not is_plugin_enabled(session, manifest.plugin_id):
            continue
        for (
            section_kind,
            section_id,
            private_key,
            builder,
            _apply,
        ) in manifest.entity_form_sections:
            if section_kind != cleaned_kind:
                continue
            try:
                built = builder(session, entity) or {}
            except Exception as exc:
                return {
                    "ok": False,
                    "message": f"Plugin {manifest.plugin_id!r} form section failed: {exc}",
                }
            fields = list(built.get("fields") or [])
            prefix = field_prefix(manifest.plugin_id, section_id)
            # Rewrite showWhen field refs to prefixed modal names.
            rewritten: list[dict[str, Any]] = []
            for field in fields:
                if not isinstance(field, dict):
                    continue
                item = dict(field)
                name = str(item.get("name") or "").strip()
                if not name:
                    continue
                item["name"] = prefix + name
                show_when = item.get("showWhen")
                if isinstance(show_when, dict) and show_when.get("field"):
                    item["showWhen"] = {
                        **show_when,
                        "field": prefix + str(show_when["field"]).strip(),
                    }
                item["group"] = "plugins"
                rewritten.append(item)
            sections.append(
                {
                    "plugin_id": manifest.plugin_id,
                    "plugin_label": manifest.label,
                    "section_id": section_id,
                    "private_key": private_key,
                    "title": str(built.get("title") or manifest.label),
                    "fields": rewritten,
                }
            )
    return {"ok": True, "kind": cleaned_kind, "sections": sections}


def merge_entity_form_private_data(
    session,
    kind: str,
    private_data: str,
    form_values: dict[str, Any],
) -> dict[str, Any]:
    """
    Apply enabled plugin form field values onto *private_data* JSON text.

    Returns ``{ok, private_data?, message?}``.
    """
    cleaned_kind = (kind or "").strip().lower()
    if cleaned_kind not in ("object", "agent"):
        return {"ok": False, "message": "kind must be 'object' or 'agent'."}

    blob, err = _parse_private_dict(private_data)
    if err:
        return {"ok": False, "message": err}
    assert blob is not None

    values = form_values if isinstance(form_values, dict) else {}
    for manifest in list_installed_plugins():
        if not is_plugin_enabled(session, manifest.plugin_id):
            continue
        for (
            section_kind,
            section_id,
            private_key,
            _builder,
            apply_values,
        ) in manifest.entity_form_sections:
            if section_kind != cleaned_kind:
                continue
            prefix = field_prefix(manifest.plugin_id, section_id)
            section_vals: dict[str, Any] = {}
            for key, value in values.items():
                key_s = str(key)
                if key_s.startswith(prefix):
                    section_vals[key_s[len(prefix) :]] = value
            if not section_vals:
                continue
            existing = blob.get(private_key)
            existing_dict = existing if isinstance(existing, dict) else None
            try:
                updated = apply_values(existing_dict, section_vals)
            except Exception as exc:
                return {
                    "ok": False,
                    "message": f"Plugin {manifest.plugin_id!r} could not apply form values: {exc}",
                }
            if updated is None:
                blob.pop(private_key, None)
            else:
                blob[private_key] = updated

    if not blob:
        return {"ok": True, "private_data": ""}
    return {
        "ok": True,
        "private_data": json.dumps(blob, indent=2, sort_keys=True),
    }
