"""LLM provider interface and shared prompt-payload conventions.

No core pipeline code imports a vendor SDK directly. All providers expose:

    generate_json(system_prompt, user_prompt) -> dict

To keep the FakeLLMProvider fully deterministic (and to give real models
clean structured context), prompts embed a machine-readable JSON payload
delimited by markers. Real providers simply treat it as helpful context;
the fake provider parses it to compute a grounded, deterministic response.
"""

from __future__ import annotations

import json
from typing import Any, Protocol, runtime_checkable

PAYLOAD_START = "<<<TASK_PAYLOAD>>>"
PAYLOAD_END = "<<<END_TASK_PAYLOAD>>>"


@runtime_checkable
class LLMProvider(Protocol):
    """Common LLM provider contract."""

    name: str

    def generate_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        ...


def embed_payload(prompt: str, payload: dict[str, Any]) -> str:
    """Append a delimited JSON payload to a prompt."""
    encoded = json.dumps(payload, ensure_ascii=False)
    return f"{prompt}\n\n{PAYLOAD_START}\n{encoded}\n{PAYLOAD_END}\n"


def extract_payload(user_prompt: str) -> dict[str, Any]:
    """Extract the embedded JSON payload from a prompt, or {} if absent."""
    start = user_prompt.find(PAYLOAD_START)
    end = user_prompt.find(PAYLOAD_END)
    if start == -1 or end == -1 or end <= start:
        return {}
    raw = user_prompt[start + len(PAYLOAD_START) : end].strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


class LLMError(RuntimeError):
    """Raised when a provider cannot fulfil a request."""
