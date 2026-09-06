from src.analysis import equivalent_input_token_cost, matched_deltas, p95, summarize


def test_equivalent_input_cost_rules() -> None:
    assert equivalent_input_token_cost({"strategy": "cold_control", "prompt_tokens": 1000}) == 1000
    assert equivalent_input_token_cost({"strategy": "implicit", "prompt_tokens": 1000, "cached_tokens": 800}) == 360
    assert equivalent_input_token_cost({"strategy": "explicit", "prompt_tokens": 1000, "cache_creation_input_tokens": 800}) == 1200
    assert equivalent_input_token_cost({"strategy": "explicit", "prompt_tokens": 1000, "cached_tokens": 800}) == 280


def test_p95_uses_nearest_rank() -> None:
    assert p95(list(range(1, 21))) == 19
    assert p95([]) is None


def test_summary_keeps_errors_and_success_separate() -> None:
    rows = [
        {"strategy": "cold_control", "error_type": None, "success": True, "latency_ms": 10, "prompt_tokens": 1000, "cached_tokens": 0},
        {"strategy": "cold_control", "error_type": "Timeout", "success": False, "latency_ms": 90_000},
    ]
    item = summarize(rows)["cold_control"]
    assert item["observations"] == 2
    assert item["api_errors"] == 1
    assert item["machine_successes"] == 1
    assert item["median_latency_ms"] == 10


def test_matched_deltas_require_valid_cold_pair() -> None:
    rows = [
        {"strategy": "cold_control", "length_level": "L1", "document_repetition": 1, "chain_position": 1, "error_type": None, "success": True, "latency_ms": 100, "prompt_tokens": 1000},
        {"strategy": "implicit", "length_level": "L1", "document_repetition": 1, "chain_position": 1, "error_type": None, "success": True, "latency_ms": 60, "prompt_tokens": 1000, "cached_tokens": 800},
    ]
    result = matched_deltas(rows)
    assert len(result) == 1
    assert result[0]["latency_delta_ms_vs_cold"] == -40
    assert result[0]["equivalent_input_cost_saving_pct"] == 64
