from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import random
from typing import Any

from .constants import DOCUMENT_REPETITIONS, LENGTH_LEVELS, STRATEGIES


def build_execution_plan(seed: int) -> dict[str, Any]:
    chains = [
        {
            "chain_id": f"{strategy}-{level}-d{document}",
            "strategy": strategy,
            "length_level": level,
            "document_repetition": document,
            "positions": [1, 2, 3],
        }
        for strategy in STRATEGIES
        for level in LENGTH_LEVELS
        for document in DOCUMENT_REPETITIONS
    ]
    rng = random.Random(seed)
    rng.shuffle(chains)
    observations = []
    for chain_index, chain in enumerate(chains, start=1):
        for position in chain["positions"]:
            observations.append(
                {
                    "execution_index": len(observations) + 1,
                    "chain_index": chain_index,
                    "observation_id": f"{chain['chain_id']}-q{position}",
                    "chain_id": chain["chain_id"],
                    "strategy": chain["strategy"],
                    "length_level": chain["length_level"],
                    "document_repetition": chain["document_repetition"],
                    "chain_position": position,
                }
            )
    return {"version": "draft-0.1", "seed": seed, "chain_count": len(chains), "observation_count": len(observations), "observations": observations}


def canonical_sha256(plan: dict[str, Any]) -> str:
    payload = json.dumps(plan, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plan = build_execution_plan(args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "observations": plan["observation_count"], "sha256": canonical_sha256(plan)}, ensure_ascii=False))


if __name__ == "__main__":
    main()

