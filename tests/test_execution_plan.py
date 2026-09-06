from src.execution_plan import build_execution_plan, canonical_sha256


def test_plan_has_54_unique_observations_and_18_chains() -> None:
    plan = build_execution_plan(20260906)
    assert plan["chain_count"] == 18
    assert plan["observation_count"] == 54
    ids = [item["observation_id"] for item in plan["observations"]]
    assert len(ids) == len(set(ids))


def test_chain_positions_stay_contiguous_and_ordered() -> None:
    plan = build_execution_plan(20260906)
    observations = plan["observations"]
    for offset in range(0, len(observations), 3):
        group = observations[offset : offset + 3]
        assert len({item["chain_id"] for item in group}) == 1
        assert [item["chain_position"] for item in group] == [1, 2, 3]


def test_seed_is_reproducible_and_changes_order() -> None:
    first = build_execution_plan(20260906)
    second = build_execution_plan(20260906)
    other = build_execution_plan(20260907)
    assert canonical_sha256(first) == canonical_sha256(second)
    assert [x["chain_id"] for x in first["observations"]] != [x["chain_id"] for x in other["observations"]]

