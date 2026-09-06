from __future__ import annotations

import json
from typing import Any

from .fixtures import GoldAnswer


def score_answer(raw_answer: str, gold: GoldAnswer) -> dict[str, Any]:
    result: dict[str, Any] = {"success": False, "reason": None, "parsed": None}
    try:
        parsed = json.loads(raw_answer)
    except (json.JSONDecodeError, TypeError) as exc:
        result["reason"] = f"invalid_json:{type(exc).__name__}"
        return result

    result["parsed"] = parsed
    if not isinstance(parsed, dict):
        result["reason"] = "top_level_not_object"
        return result
    if set(parsed) != {"answer", "evidence_id"}:
        result["reason"] = "schema_keys_mismatch"
        return result
    if not all(isinstance(parsed[key], str) for key in ("answer", "evidence_id")):
        result["reason"] = "schema_type_mismatch"
        return result
    if parsed["answer"] != gold.answer:
        result["reason"] = "wrong_answer"
        return result
    if parsed["evidence_id"] != gold.evidence_id:
        result["reason"] = "wrong_evidence_id"
        return result

    result["success"] = True
    result["reason"] = "exact_match"
    return result

