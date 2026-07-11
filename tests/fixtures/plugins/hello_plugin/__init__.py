"""Hello plugin fixture for plugin platform tests (not shipped in plugins/)."""

from __future__ import annotations

from campaign_rpg_engine.action_outcome import ActionOutcome

PLUGIN_ID = "hello_plugin"
PLUGIN_LABEL = "Hello Plugin"
PLUGIN_VERSION = "1"
PLUGIN_DESCRIPTION = "Test plugin for the plugin platform."


def register(ctx):
    def on_session_loaded(session, **payload):
        del payload
        session.set_extension(
            PLUGIN_ID,
            {"greeting": "hello from plugin"},
        )

    ctx.on("session_loaded", on_session_loaded)

    def wave(session, agent, area, turn):
        del session, area, turn
        return ActionOutcome(
            result="You wave hello.",
            passive_result=f"{agent.name} waves hello.",
        )

    ctx.register_turn_verb("hello_wave", wave, description="Wave hello")

    def slot_renderer(session, agent, area, ctx_prompt, options):
        del agent, area, ctx_prompt, options
        ext = session.get_extension(PLUGIN_ID) or {}
        return f"Hello plugin active: {ext.get('greeting', '')}"

    ctx.register_prompt_slot("hello_plugin", slot_renderer, description="Hello slot")

    ctx.set_panel(
        {
            "title": "Hello Plugin",
            "sections": [
                {"type": "text", "content": "Test plugin for the platform."},
                {
                    "type": "key_value_list",
                    "items": [{"key": "Plugin id", "value": PLUGIN_ID}],
                },
                {"type": "button", "id": "ping", "label": "Ping"},
            ],
        }
    )

    def ping(session, params):
        del params
        return {"ok": True, "message": "pong"}

    ctx.register_panel_action("ping", ping)
