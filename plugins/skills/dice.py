"""Dice and modifier helpers for the skills plugin."""

from __future__ import annotations

import random
from typing import Any

STAT_NAMES = ("CON", "STR", "DEX", "WIS", "INT", "CHM")
DEFAULT_STAT = 10
MIN_STAT = 1
MAX_STAT = 20


def clamp_stat(value: int) -> int:
    return max(MIN_STAT, min(MAX_STAT, int(value)))


def stat_modifier(score: int) -> int:
    """(score - 10) // 2 — 10 → +0, 20 → +5."""
    return (clamp_stat(score) - 10) // 2


def normalize_stats(raw: Any) -> dict[str, int]:
    stats = {name: DEFAULT_STAT for name in STAT_NAMES}
    if not isinstance(raw, dict):
        return stats
    for name in STAT_NAMES:
        if name in raw:
            try:
                stats[name] = clamp_stat(int(raw[name]))
            except (TypeError, ValueError):
                pass
    return stats


def normalize_skills(raw: Any) -> dict[str, int]:
    skills: dict[str, int] = {}
    if not isinstance(raw, dict):
        return skills
    for key, value in raw.items():
        name = str(key).strip()
        if not name:
            continue
        try:
            skills[name] = int(value)
        except (TypeError, ValueError):
            continue
    return skills


def roll_d20(*, rng: random.Random | None = None) -> int:
    roller = rng if rng is not None else random
    return roller.randint(1, 20)


def resolve_check(
    *,
    stats: dict[str, int],
    skills: dict[str, int],
    stat: str,
    skill: str | None,
    dc: int,
    roll: int | None = None,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """Return roll breakdown and whether the check passed."""
    stat_key = stat.strip().upper()
    score = stats.get(stat_key, DEFAULT_STAT)
    mod = stat_modifier(score)
    skill_name = (skill or "").strip()
    skill_bonus = int(skills.get(skill_name, 0)) if skill_name else 0
    die = roll if roll is not None else roll_d20(rng=rng)
    total = die + mod + skill_bonus
    parts = [f"d20={die}", f"{stat_key}{mod:+d}"]
    if skill_name:
        parts.append(f"{skill_name}{skill_bonus:+d}")
    return {
        "stat": stat_key,
        "skill": skill_name or None,
        "score": score,
        "modifier": mod,
        "skill_bonus": skill_bonus,
        "roll": die,
        "total": total,
        "dc": int(dc),
        "passed": total >= int(dc),
        "detail": f"{'+'.join(parts)}={total} vs DC {dc}",
    }
