from src.smoke_plan import build_smoke_plan


def test_smoke_plan_has_exactly_six_unique_requests() -> None:
    plan = build_smoke_plan()
    observations = plan["observations"]
    assert plan["observation_count"] == 6
    assert len(observations) == 6
    assert len({row["observation_id"] for row in observations}) == 6


def test_smoke_covers_all_lengths_and_strategies() -> None:
    observations = build_smoke_plan()["observations"]
    assert {row["length_level"] for row in observations} == {"L1", "L2", "L3"}
    assert {row["strategy"] for row in observations} == {"cold_control", "implicit", "explicit"}


def test_smoke_pairs_are_contiguous() -> None:
    observations = build_smoke_plan()["observations"]
    for offset in (0, 2, 4):
        pair = observations[offset : offset + 2]
        assert pair[0]["chain_id"] == pair[1]["chain_id"]
        assert [row["chain_position"] for row in pair] == [1, 2]
