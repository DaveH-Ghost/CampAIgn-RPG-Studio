"""Dice helpers for combat (damage + attack rolls)."""

from __future__ import annotations

import random
import re
from typing import Any

_DAMAGE_RE = re.compile(
    r"^\s*(\d+)d(\d+)([+-]\d+)?\s*$",
    re.IGNORECASE,
)


def parse_damage(expr: str) -> tuple[int, int, int] | str:
    """Parse ``NdM+mod`` into (n, sides, mod) or an error string."""
    cleaned = (expr or "").strip()
    match = _DAMAGE_RE.match(cleaned)
    if not match:
        return f"Invalid damage expression {expr!r}; expected NdM or NdM+mod."
    n = int(match.group(1))
    sides = int(match.group(2))
    mod = int(match.group(3) or 0)
    if n < 1 or sides < 1:
        return f"Invalid damage expression {expr!r}."
    return n, sides, mod


def roll_damage(expr: str, *, rng: random.Random | None = None) -> dict[str, Any] | str:
    parsed = parse_damage(expr)
    if isinstance(parsed, str):
        return parsed
    n, sides, mod = parsed
    roller = rng if rng is not None else random
    rolls = [roller.randint(1, sides) for _ in range(n)]
    total = sum(rolls) + mod
    detail = f"{n}d{sides}" + (f"{mod:+d}" if mod else "") + f"={total}"
    if n > 1 or mod:
        detail = f"{'+'.join(str(r) for r in rolls)}" + (f"{mod:+d}" if mod else "") + f"={total}"
    return {
        "expr": expr.strip(),
        "rolls": rolls,
        "modifier": mod,
        "total": max(0, total),
        "detail": detail,
    }


def roll_d20(*, rng: random.Random | None = None) -> int:
    roller = rng if rng is not None else random
    return roller.randint(1, 20)
