from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def build_smoke_plan() -> dict[str, Any]:
    """Return the fixed six-request pre-live mechanics check."""
    rows = [
        ("implicit", "L1", 1, 1),
        ("implicit", "L1", 1, 2),
        ("explicit", "L2", 1, 1),
        ("explicit", "L2", 1, 2),
        ("cold_control", "L3", 1, 1),
        ("cold_control", "L3", 1, 2),
    ]
    observations = []
    for index, (strategy, level, repetition, position) in enumerate(rows, start=1):
        chain_id = f"smoke-{strategy}-{level}-d{repetition}"
        observations.append(
            {
                "execution_index": index,
                "observation_id": f"{chain_id}-q{position}",
                "chain_id": chain_id,
                "strategy": strategy,
                "length_level": level,
                "document_repetition": repetition,
                "chain_position": position,
            }
        )
    return {"version": "draft-0.2", "observation_count": 6, "observations": observations}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plan = build_smoke_plan()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "observations": 6}, ensure_ascii=False))


if __name__ == "__main__":
    main()
