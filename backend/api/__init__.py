"""Domain-grouped FastAPI routers for campaign-rpg-studio.

Each submodule owns one domain of ``/api`` routes. ``register_routers`` wires
them all onto the app so ``backend.app.create_app`` can stay thin. URL paths and
response shapes are unchanged from the pre-split monolithic ``app.py``.
"""

from __future__ import annotations

from fastapi import FastAPI

from backend.api import (
    lorebooks,
    misc,
    player,
    plugins,
    prompt,
    session,
    settings,
    templates,
    turn,
    world,
)

ROUTERS = (
    session.router,
    turn.router,
    prompt.router,
    world.router,
    templates.router,
    lorebooks.router,
    plugins.router,
    settings.router,
    misc.router,
    player.router,
)


def register_routers(app: FastAPI) -> None:
    """Include every domain router onto ``app``."""
    for router in ROUTERS:
        app.include_router(router)
