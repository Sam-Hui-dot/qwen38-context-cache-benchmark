from __future__ import annotations

import hashlib
import json
from typing import Any

from .constants import (
    ENABLE_THINKING,
    MAX_TOKENS,
    MODEL,
    NONCE_HEX_LENGTH,
    STABLE_NONCE_HEX,
    SYSTEM_CONTRACT,
    TEMPERATURE,
)
from .fixtures import DocumentFixture


def _nonce(strategy: str, observation_id: str) -> str:
    if strategy == "cold_control":
        digest = hashlib.sha256(observation_id.encode("utf-8")).hexdigest()[:NONCE_HEX_LENGTH]
        return f"REQUEST-NONCE-{digest}"
    if strategy in {"implicit", "explicit"}:
        # Keep B/C prompt text byte-identical; C differs only by cache_control metadata.
        return f"REQUEST-NONCE-{STABLE_NONCE_HEX}"
    raise ValueError(f"unknown strategy: {strategy}")


def build_request(
    fixture: DocumentFixture,
    strategy: str,
    chain_position: int,
    observation_id: str,
) -> dict[str, Any]:
    if chain_position not in (1, 2, 3):
        raise ValueError("chain_position must be 1, 2, or 3")

    document_block: dict[str, Any] = {"type": "text", "text": fixture.text}
    if strategy == "explicit":
        document_block["cache_control"] = {"type": "ephemeral"}

    content = [
        {"type": "text", "text": _nonce(strategy, observation_id)},
        {"type": "text", "text": SYSTEM_CONTRACT},
        document_block,
    ]
    return {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": content},
            {"role": "user", "content": fixture.questions[chain_position - 1]},
        ],
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
        "enable_thinking": ENABLE_THINKING,
    }


def request_sha256(request: dict[str, Any]) -> str:
    canonical = json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
