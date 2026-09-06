import json

from src.fixtures import build_fixture
from src.runner import parse_response, run_observation


def test_parse_response_preserves_cache_usage_and_reasoning() -> None:
    parsed = parse_response(
        {
            "id": "resp-1",
            "created": 123,
            "system_fingerprint": "fp",
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"content": "{}", "reasoning_content": None},
                }
            ],
            "usage": {
                "prompt_tokens": 2000,
                "completion_tokens": 10,
                "total_tokens": 2010,
                "prompt_tokens_details": {
                    "cached_tokens": 1500,
                    "cache_creation_input_tokens": 0,
                },
                "completion_tokens_details": {"reasoning_tokens": 0},
            },
        }
    )
    assert parsed["cached_tokens"] == 1500
    assert parsed["cache_creation_input_tokens"] == 0
    assert parsed["reasoning_tokens"] == 0
    assert parsed["response_id"] == "resp-1"


def test_observation_records_success_without_secrets() -> None:
    item = {
        "execution_index": 1,
        "observation_id": "implicit-L1-d1-q1",
        "chain_id": "implicit-L1-d1",
        "strategy": "implicit",
        "length_level": "L1",
        "document_repetition": 1,
        "chain_position": 1,
    }
    fixture = build_fixture("L1", 1)
    gold = fixture.gold[0]

    def sender(payload, answer, evidence):
        assert answer == gold.answer
        assert evidence == gold.evidence_id
        return {
            "id": "resp-ok",
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "content": json.dumps({"answer": answer, "evidence_id": evidence}),
                        "reasoning_content": None,
                    },
                }
            ],
            "usage": {"prompt_tokens": 2000, "completion_tokens": 20, "total_tokens": 2020},
        }

    record = run_observation(item, "smoke", sender, ("SECRET_VALUE",))
    assert record["success"] is True
    assert record["error_type"] is None
    assert "SECRET_VALUE" not in json.dumps(record)
    assert record["request_sha256"]
    assert record["document_sha256"]


def test_observation_scrubs_error_and_never_retries_sender() -> None:
    item = {
        "execution_index": 1,
        "observation_id": "cold-L1-d1-q1",
        "chain_id": "cold-L1-d1",
        "strategy": "cold_control",
        "length_level": "L1",
        "document_repetition": 1,
        "chain_position": 1,
    }
    calls = 0

    def failing_sender(payload, answer, evidence):
        nonlocal calls
        calls += 1
        raise RuntimeError("request to workspace-SECRET failed with key-SECRET")

    record = run_observation(item, "smoke", failing_sender, ("workspace-SECRET", "key-SECRET"))
    assert calls == 1
    assert record["success"] is False
    assert record["error_type"] == "RuntimeError"
    assert "SECRET" not in record["error_message"]

