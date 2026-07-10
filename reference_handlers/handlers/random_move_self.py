"""random_move_self reference handler."""

from __future__ import annotations

import random

from realm_fabric import object_footprint_tiles


def random_move_self(session, area, agent, obj, action) -> str | None:
    del session, agent, action
    occupied = set(object_footprint_tiles(obj))
    positions = [
        (x, y)
        for x in range(area.min_x, area.max_x + 1)
        for y in range(area.min_y, area.max_y + 1)
        if (x, y) not in occupied
    ]
    if not positions:
        return None
    obj.position = random.choice(positions)
    return None
