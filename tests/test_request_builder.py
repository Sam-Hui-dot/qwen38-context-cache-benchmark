from src.fixtures import build_fixture
from src.request_builder import build_request


def _document_block(request: dict) -> dict:
    return request["messages"][0]["content"][2]


def test_all_conditions_keep_core_model_parameters_fixed() -> None:
    fixture = build_fixture("L1", 1)
    requests = [build_request(fixture, strategy, 1, f"obs-{strategy}") for strategy in ("cold_control", "implicit", "explicit")]
    for request in requests:
        assert request["model"] == "qwen3.8-27b"
        assert request["temperature"] == 0
        assert request["max_tokens"] == 128
        assert request["enable_thinking"] is False
        assert request["messages"][1]["content"] == fixture.questions[0]
        assert _document_block(request)["text"] == fixture.text


def test_only_explicit_condition_has_cache_control() -> None:
    fixture = build_fixture("L1", 1)
    cold = build_request(fixture, "cold_control", 1, "cold-1")
    implicit = build_request(fixture, "implicit", 1, "implicit-1")
    explicit = build_request(fixture, "explicit", 1, "explicit-1")
    assert "cache_control" not in _document_block(cold)
    assert "cache_control" not in _document_block(implicit)
    assert _document_block(explicit)["cache_control"] == {"type": "ephemeral"}


def test_cold_nonce_changes_but_implicit_and_explicit_are_stable() -> None:
    fixture = build_fixture("L1", 1)
    cold_1 = build_request(fixture, "cold_control", 1, "cold-1")
    cold_2 = build_request(fixture, "cold_control", 2, "cold-2")
    implicit_1 = build_request(fixture, "implicit", 1, "implicit-1")
    implicit_2 = build_request(fixture, "implicit", 2, "implicit-2")
    explicit_1 = build_request(fixture, "explicit", 1, "explicit-1")
    explicit_2 = build_request(fixture, "explicit", 2, "explicit-2")
    assert cold_1["messages"][0]["content"][0] != cold_2["messages"][0]["content"][0]
    assert implicit_1["messages"][0] == implicit_2["messages"][0]
    assert explicit_1["messages"][0] == explicit_2["messages"][0]


def test_condition_nonce_text_is_equal_length_and_b_c_are_identical() -> None:
    fixture = build_fixture("L1", 1)
    requests = {
        strategy: build_request(fixture, strategy, 1, f"obs-{strategy}")
        for strategy in ("cold_control", "implicit", "explicit")
    }
    nonce_texts = {
        strategy: request["messages"][0]["content"][0]["text"]
        for strategy, request in requests.items()
    }
    assert len({len(value) for value in nonce_texts.values()}) == 1
    assert nonce_texts["implicit"] == nonce_texts["explicit"]
    assert nonce_texts["cold_control"] != nonce_texts["implicit"]


def test_invalid_strategy_and_position_fail() -> None:
    fixture = build_fixture("L1", 1)
    try:
        build_request(fixture, "unknown", 1, "obs")
    except ValueError:
        pass
    else:
        raise AssertionError("unknown strategy must fail")

    try:
        build_request(fixture, "implicit", 4, "obs")
    except ValueError:
        pass
    else:
        raise AssertionError("invalid chain position must fail")
