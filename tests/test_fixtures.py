import pytest

from src.fixtures import build_all_fixtures, build_fixture


def test_builds_six_unique_fixtures() -> None:
    fixtures = build_all_fixtures()
    assert len(fixtures) == 6
    assert len({fixture.sha256 for fixture in fixtures}) == 6
    assert len({fixture.fixture_id for fixture in fixtures}) == 6


def test_length_levels_are_strictly_increasing() -> None:
    sizes = [len(build_fixture(level, 1).text) for level in ("L1", "L2", "L3")]
    assert sizes == sorted(sizes)
    assert len(set(sizes)) == 3


def test_offline_character_sizes_are_in_calibrated_ranges() -> None:
    ranges = {
        "L1": (3_000, 5_000),
        "L2": (10_000, 14_000),
        "L3": (18_000, 22_000),
    }
    for level, (minimum, maximum) in ranges.items():
        size = len(build_fixture(level, 1).text)
        assert minimum <= size <= maximum


@pytest.mark.parametrize("level", ["L1", "L2", "L3"])
@pytest.mark.parametrize("repetition", [1, 2])
def test_gold_occurs_once_and_evidence_exists(level: str, repetition: int) -> None:
    fixture = build_fixture(level, repetition)
    for gold in fixture.gold:
        assert fixture.text.count(gold.answer) == 1
        assert fixture.text.count(f'"id": "{gold.evidence_id}"') == 1


def test_invalid_fixture_parameters_fail() -> None:
    with pytest.raises(ValueError):
        build_fixture("L9", 1)
    with pytest.raises(ValueError):
        build_fixture("L1", 3)
