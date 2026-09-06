from src.review_smoke import review


def _valid_rows():
    rows = []
    specs = [
        ("implicit", "L1", 1, 2000, 0, 0),
        ("implicit", "L1", 2, 2000, 1500, 0),
        ("explicit", "L2", 1, 6000, 0, 5500),
        ("explicit", "L2", 2, 6000, 5500, 0),
        ("cold_control", "L3", 1, 10000, 0, 0),
        ("cold_control", "L3", 2, 10000, 0, 0),
    ]
    for index, (strategy, level, position, prompt, cached, created) in enumerate(specs, start=1):
        rows.append(
            {
                "observation_id": f"obs-{index}",
                "strategy": strategy,
                "length_level": level,
                "chain_position": position,
                "prompt_tokens": prompt,
                "cached_tokens": cached,
                "cache_creation_input_tokens": created,
                "enable_thinking": False,
                "reasoning_content": None,
                "success": True,
                "error_type": None,
            }
        )
    return rows


def test_valid_smoke_passes() -> None:
    result = review(_valid_rows())
    assert result["pass"] is True
    assert all(result["checks"].values())


def test_missing_cache_hit_fails() -> None:
    rows = _valid_rows()
    rows[1]["cached_tokens"] = 0
    result = review(rows)
    assert result["pass"] is False
    assert result["checks"]["implicit_second_hit"] is False


def test_out_of_band_prompt_length_fails() -> None:
    rows = _valid_rows()
    rows[0]["prompt_tokens"] = 500
    rows[1]["prompt_tokens"] = 500
    result = review(rows)
    assert result["pass"] is False
    assert result["checks"]["length_bands"] is False


def test_reasoning_content_fails_thinking_off_check() -> None:
    rows = _valid_rows()
    rows[0]["reasoning_content"] = "unexpected"
    result = review(rows)
    assert result["pass"] is False
    assert result["checks"]["no_reasoning_content"] is False
