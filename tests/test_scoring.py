import json

import pytest

from src.fixtures import GoldAnswer
from src.scoring import score_answer


GOLD = GoldAnswer(answer="OWNER-L1-1-KAPPA", evidence_id="REC-0017")


def test_exact_answer_passes() -> None:
    raw = json.dumps({"answer": GOLD.answer, "evidence_id": GOLD.evidence_id})
    assert score_answer(raw, GOLD)["success"] is True


@pytest.mark.parametrize(
    "raw,reason",
    [
        ("not json", "invalid_json:JSONDecodeError"),
        ('["OWNER-L1-1-KAPPA", "REC-0017"]', "top_level_not_object"),
        ('{"answer":"OWNER-L1-1-KAPPA"}', "schema_keys_mismatch"),
        ('{"answer":"OWNER-L1-1-KAPPA","evidence_id":"REC-0017","note":"ok"}', "schema_keys_mismatch"),
        ('{"answer":7,"evidence_id":"REC-0017"}', "schema_type_mismatch"),
        ('{"answer":"WRONG","evidence_id":"REC-0017"}', "wrong_answer"),
        ('{"answer":"OWNER-L1-1-KAPPA","evidence_id":"REC-9999"}', "wrong_evidence_id"),
        ('```json\n{"answer":"OWNER-L1-1-KAPPA","evidence_id":"REC-0017"}\n```', "invalid_json:JSONDecodeError"),
    ],
)
def test_adversarial_answers_fail(raw: str, reason: str) -> None:
    result = score_answer(raw, GOLD)
    assert result["success"] is False
    assert result["reason"] == reason

