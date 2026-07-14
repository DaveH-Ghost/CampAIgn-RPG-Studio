"""Guards against reintroducing plugin-specific hardcoding in Studio frontend."""

from __future__ import annotations

from pathlib import Path

FRONTEND = Path(__file__).resolve().parents[1] / "frontend"

# Handler ids / inventory prefixes must not appear in frontend source (docs comments ok
# only if they avoid these exact tokens — keep the tree clean).
_FORBIDDEN = (
    "skill_check",
    "pass_handler",
    "inventory_",
)


def test_frontend_has_no_plugin_handler_hardcoding():
    offenders: list[str] = []
    for path in sorted(FRONTEND.rglob("*")):
        if path.suffix not in {".js", ".html", ".css"}:
            continue
        text = path.read_text(encoding="utf-8")
        for token in _FORBIDDEN:
            if token in text:
                offenders.append(f"{path.relative_to(FRONTEND.parent)}: contains {token!r}")
    assert not offenders, "Plugin-specific tokens in frontend:\n" + "\n".join(offenders)
