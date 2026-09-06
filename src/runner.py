from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any, Callable

from dotenv import load_dotenv

from .constants import ENABLE_THINKING, MAX_TOKENS, MODEL, SYSTEM_CONTRACT, TEMPERATURE
from .fixtures import build_fixture
from .request_builder import build_request, request_sha256
from .scoring import score_answer


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TIMEOUT_SECONDS = 90


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _scrub(text: str, secrets: tuple[str, ...]) -> str:
    cleaned = text
    for secret in secrets:
        if secret:
            cleaned = cleaned.replace(secret, "<redacted>")
    return cleaned


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _message_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "".join(parts)
    return ""


def parse_response(response: dict[str, Any]) -> dict[str, Any]:
    choices = response.get("choices") if isinstance(response.get("choices"), list) else []
    choice = _as_dict(choices[0]) if choices else {}
    message = _as_dict(choice.get("message"))
    usage = _as_dict(response.get("usage"))
    prompt_details = _as_dict(usage.get("prompt_tokens_details"))
    if not prompt_details:
        prompt_details = _as_dict(usage.get("input_tokens_details"))
    completion_details = _as_dict(usage.get("completion_tokens_details"))

    return {
        "response_id": response.get("id"),
        "created": response.get("created"),
        "system_fingerprint": response.get("system_fingerprint"),
        "finish_reason": choice.get("finish_reason"),
        "final_answer": _message_text(message.get("content")),
        "reasoning_content": message.get("reasoning_content"),
        "prompt_tokens": usage.get("prompt_tokens", usage.get("input_tokens")),
        "cached_tokens": prompt_details.get("cached_tokens"),
        "cache_creation_input_tokens": prompt_details.get("cache_creation_input_tokens"),
        "completion_tokens": usage.get("completion_tokens", usage.get("output_tokens")),
        "reasoning_tokens": completion_details.get("reasoning_tokens"),
        "total_tokens": usage.get("total_tokens"),
    }


def mock_sender(payload: dict[str, Any], gold_answer: str, gold_evidence: str) -> dict[str, Any]:
    system_blocks = payload["messages"][0]["content"]
    nonce = system_blocks[0]["text"]
    document = system_blocks[2]["text"]
    question = payload["messages"][1]["content"]
    explicit = "cache_control" in system_blocks[2]
    stable = nonce.endswith("0" * 32)
    position = 1 if "owner_code" in question else 2 if "approval_limit" in question else 3
    if len(document) < 10_000:
        prompt_tokens = 2_000
    elif len(document) < 25_000:
        prompt_tokens = 6_000
    else:
        prompt_tokens = 10_000
    cached_tokens = 0
    created_tokens = 0
    if explicit:
        if position == 1:
            created_tokens = prompt_tokens - 500
        else:
            cached_tokens = prompt_tokens - 500
    elif stable and position > 1:
        cached_tokens = prompt_tokens - 500
    return {
        "id": "mock-response",
        "created": 0,
        "system_fingerprint": "mock",
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "content": json.dumps(
                        {"answer": gold_answer, "evidence_id": gold_evidence},
                        ensure_ascii=False,
                    ),
                    "reasoning_content": None,
                },
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": 20,
            "total_tokens": prompt_tokens + 20,
            "prompt_tokens_details": {
                "cached_tokens": cached_tokens,
                "cache_creation_input_tokens": created_tokens,
            },
        },
    }


def make_live_sender(api_key: str, workspace_id: str) -> Callable[[dict[str, Any], str, str], dict[str, Any]]:
    import requests
    from requests.adapters import HTTPAdapter

    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=0))
    url = f"https://{workspace_id}.cn-beijing.maas.aliyuncs.com/compatible-mode/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    def send(payload: dict[str, Any], _gold_answer: str, _gold_evidence: str) -> dict[str, Any]:
        response = session.post(url, headers=headers, json=payload, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        parsed = response.json()
        if not isinstance(parsed, dict):
            raise ValueError("API response is not a JSON object")
        return parsed

    return send


def run_observation(
    item: dict[str, Any],
    phase: str,
    sender: Callable[[dict[str, Any], str, str], dict[str, Any]],
    secrets: tuple[str, ...] = (),
) -> dict[str, Any]:
    fixture = build_fixture(item["length_level"], int(item["document_repetition"]))
    position = int(item["chain_position"])
    gold = fixture.gold[position - 1]
    payload = build_request(fixture, item["strategy"], position, item["observation_id"])
    started_at = datetime.now(timezone.utc).isoformat()
    started = time.perf_counter()
    base = {
        "phase": phase,
        "timestamp": started_at,
        **item,
        "model": MODEL,
        "enable_thinking": ENABLE_THINKING,
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
        "timeout_seconds": TIMEOUT_SECONDS,
        "fixture_id": fixture.fixture_id,
        "document_sha256": fixture.sha256,
        "stable_prefix_sha256": _sha256_text(SYSTEM_CONTRACT + "\n" + fixture.text),
        "request_sha256": request_sha256(payload),
    }
    try:
        response = sender(payload, gold.answer, gold.evidence_id)
        parsed = parse_response(response)
        grade = score_answer(parsed["final_answer"], gold)
        return {
            **base,
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
            **parsed,
            "success": grade["success"],
            "grader_result": grade,
            "error_type": None,
            "error_message": None,
            "raw_response": response,
        }
    except Exception as exc:  # one observation, one request, no retry
        return {
            **base,
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
            "response_id": None,
            "created": None,
            "system_fingerprint": None,
            "finish_reason": None,
            "final_answer": None,
            "reasoning_content": None,
            "prompt_tokens": None,
            "cached_tokens": None,
            "cache_creation_input_tokens": None,
            "completion_tokens": None,
            "reasoning_tokens": None,
            "total_tokens": None,
            "success": False,
            "grader_result": None,
            "error_type": type(exc).__name__,
            "error_message": _scrub(str(exc), secrets),
            "raw_response": None,
        }


def _load_plan(path: Path) -> dict[str, Any]:
    plan = json.loads(path.read_text(encoding="utf-8"))
    observations = plan.get("observations")
    if not isinstance(observations, list) or len(observations) != plan.get("observation_count"):
        raise ValueError("invalid execution plan")
    ids = [item.get("observation_id") for item in observations]
    if None in ids or len(ids) != len(set(ids)):
        raise ValueError("duplicate or missing observation_id")
    return plan


def _existing_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    ids = [row["observation_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise RuntimeError("result file contains duplicate observation IDs")
    return set(ids)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("mock", "live"), required=True)
    parser.add_argument("--phase", choices=("smoke", "formal"), required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resume", action="store_true", help="skip recorded IDs; never resend them")
    args = parser.parse_args()

    plan = _load_plan(args.plan)
    expected = 6 if args.phase == "smoke" else 54
    if plan["observation_count"] != expected:
        raise SystemExit(f"{args.phase} plan must contain exactly {expected} observations")

    existing = _existing_ids(args.output)
    if existing and not args.resume:
        raise SystemExit("output already contains observations; use --resume to skip them without resending")

    if args.mode == "mock":
        sender = mock_sender
        secrets: tuple[str, ...] = ()
    else:
        load_dotenv(PROJECT_ROOT / ".env", override=False)
        key = os.getenv("DASHSCOPE_API_KEY", "")
        workspace = os.getenv("BAILIAN_WORKSPACE_ID", "")
        approved = os.getenv("QWEN_CACHE_LIVE_APPROVED", "")
        missing = [name for name, value in (("DASHSCOPE_API_KEY", key), ("BAILIAN_WORKSPACE_ID", workspace)) if not value]
        if missing:
            raise SystemExit("missing required environment variables: " + ", ".join(missing))
        if approved != "YES":
            raise SystemExit("live gate closed: set QWEN_CACHE_LIVE_APPROVED=YES after freeze review")
        if args.phase == "formal":
            gate = PROJECT_ROOT / "reports" / "FORMAL_GATE_V2.json"
            if not gate.exists() or json.loads(gate.read_text(encoding="utf-8")).get("pass") is not True:
                raise SystemExit("formal gate closed: passing pre-formal v2 review is required")
        sender = make_live_sender(key, workspace)
        secrets = (key, workspace)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    sent = 0
    with args.output.open("a", encoding="utf-8", newline="\n") as handle:
        for item in plan["observations"]:
            if item["observation_id"] in existing:
                continue
            record = run_observation(item, args.phase, sender, secrets)
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
            handle.flush()
            sent += 1
    print(json.dumps({"mode": args.mode, "phase": args.phase, "new_records": sent, "total_records": len(existing) + sent}, ensure_ascii=False))


if __name__ == "__main__":
    main()
