"""Shared helpers for building agent inputs from state slices."""


def numbered(items: list[str]) -> str:
    """Render a list as a 1-indexed numbered block."""
    return "\n".join(f"{i}. {item}" for i, item in enumerate(items, start=1))


def clip(text: str, limit: int = 4000) -> str:
    """Truncate text to ``limit`` characters with an ellipsis."""
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + " …"
