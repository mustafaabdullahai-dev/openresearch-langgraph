"""Central prompt template registry.

Prompts live as standalone ``.txt`` files so that agent logic stays
separate from prompt content. Templates are loaded once and cached.
"""

from functools import cache
from pathlib import Path

_PROMPT_DIR = Path(__file__).parent


@cache
def load_prompt(name: str) -> str:
    """Load a prompt template ``{name}.txt`` from the prompts directory."""
    path = _PROMPT_DIR / f"{name}.txt"
    return path.read_text(encoding="utf-8")


__all__ = ["load_prompt"]
