from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import random

from .constants import LENGTH_LEVELS


@dataclass(frozen=True)
class GoldAnswer:
    answer: str
    evidence_id: str


@dataclass(frozen=True)
class DocumentFixture:
    fixture_id: str
    level: str
    seed: int
    text: str
    questions: tuple[str, str, str]
    gold: tuple[GoldAnswer, GoldAnswer, GoldAnswer]

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()


REGIONS = ("华北", "华东", "华南", "西南")
SERVICES = ("atlas", "beacon", "cobalt", "delta")
STATES = ("OPEN", "CLOSED", "WATCH")


def _record(record_id: str, rng: random.Random) -> dict[str, object]:
    return {
        "id": record_id,
        "region": rng.choice(REGIONS),
        "service": rng.choice(SERVICES),
        "state": rng.choice(STATES),
        "amount": rng.randint(100, 9999),
        "event_time": f"2026-08-{rng.randint(1, 28):02d}T{rng.randint(0, 23):02d}:{rng.randint(0, 59):02d}:00Z",
        "risk_code": rng.choice(("NONE", "NONE", "R1", "R2")),
    }


def build_fixture(level: str, repetition: int) -> DocumentFixture:
    if level not in LENGTH_LEVELS:
        raise ValueError(f"unknown level: {level}")
    if repetition not in (1, 2):
        raise ValueError("repetition must be 1 or 2")

    seed = 20260906 + 1000 * tuple(LENGTH_LEVELS).index(level) + repetition
    rng = random.Random(seed)
    count = LENGTH_LEVELS[level]
    rows = [_record(f"REC-{i:04d}", rng) for i in range(1, count + 1)]

    target_indexes = (count // 5, count // 2, count - count // 7)
    target_values = (
        f"OWNER-{level}-{repetition}-KAPPA",
        f"LIMIT-{10000 + seed % 7919}",
        f"TICKET-{seed % 100000:05d}",
    )
    target_fields = ("owner_code", "approval_limit", "rollback_ticket")
    for idx, field, value in zip(target_indexes, target_fields, target_values, strict=True):
        rows[idx][field] = value

    header = {
        "fixture": f"ledger-{level.lower()}-{repetition}",
        "generated": "2026-09-06T00:00:00Z",
        "record_count": count,
        "notice": "所有记录均为合成数据；同名字段以所在记录为准。",
    }
    lines = ["# SYNTHETIC BUSINESS LEDGER", json.dumps(header, ensure_ascii=False, sort_keys=True)]
    lines.extend(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)

    questions = (
        "找出台账中唯一的 owner_code，并返回其值及所在记录 id。",
        "找出台账中唯一的 approval_limit，并返回其值及所在记录 id。",
        "找出台账中唯一的 rollback_ticket，并返回其值及所在记录 id。",
    )
    gold = tuple(
        GoldAnswer(answer=value, evidence_id=rows[idx]["id"])
        for idx, value in zip(target_indexes, target_values, strict=True)
    )
    return DocumentFixture(
        fixture_id=f"ledger-{level.lower()}-{repetition}",
        level=level,
        seed=seed,
        text="\n".join(lines),
        questions=questions,
        gold=gold,  # type: ignore[arg-type]
    )


def build_all_fixtures() -> tuple[DocumentFixture, ...]:
    return tuple(build_fixture(level, repetition) for level in LENGTH_LEVELS for repetition in (1, 2))

