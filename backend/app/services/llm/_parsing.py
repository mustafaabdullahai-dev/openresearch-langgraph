"""Shared parsing helpers for LLM provider output.

Models rarely emit the exact JSON we ask for — they wrap it in prose,
markdown fences, or trailing explanations. These helpers normalize that
output before schema validation.
"""

from __future__ import annotations

import json
import re
from typing import Any

from .errors import StructuredOutputError

_THINKING_RE = re.compile(r"<thinking>.*?</thinking>", re.DOTALL | re.IGNORECASE)


def strip_thinking(text: str) -> str:
    """Remove Qwen-family chain-of-thought blocks from model output.

    Hosted endpoints (e.g. Groq) often leave ``<thinking>...</thinking>``
    reasoning tokens inline in ``content``. Strip that internal reasoning so
    free-form output (like reports) contains only the actual answer.
    """
    stripped = _THINKING_RE.sub("", text)
    return stripped.strip()


def strip_code_fences(text: str) -> str:
    """Remove leading/trailing markdown fences and surrounding whitespace."""
    text = text.strip()
    if text.startswith("```"):
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1 :].strip()
        text = text.removeprefix("```").strip()
    if text.endswith("```"):
        text = text[: -len("```")].rstrip()
    return text.strip()


def extract_json_object(text: str) -> dict[str, Any]:
    """Leniently extract a JSON object from model output.

    Try a direct parse first, then fall back to slicing between the
    outermost braces so prose around the JSON does not break parsing.
    """
    text = strip_thinking(text)
    text = strip_code_fences(text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError as exc:
                raise StructuredOutputError("Model returned invalid JSON.") from exc
        raise StructuredOutputError(
            "Model output did not contain a JSON object."
        ) from None
