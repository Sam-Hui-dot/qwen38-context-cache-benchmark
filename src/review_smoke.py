from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from statistics import median
from typing import Any

from .constants import TARGET_PROMPT_TOKEN_BANDS


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def review(rows: list[dict[str, Any]]) -> dict[str, Any]:
    checks: dict[str, bool] = {}
    checks["exactly_six_unique"] = len(rows) == 6 and len({r.get("observation_id") for r in rows}) == 6
    checks["all_http_success"] = all(r.get("error_type") is None for r in rows)
    checks["all_machine_success"] = all(r.get("success") is True for r in rows)
    checks["thinking_off"] = all(r.get("enable_thinking") is False for r in rows)
    checks["no_reasoning_content"] = all(not r.get("reasoning_content") for r in rows)

    by_level: dict[str, list[int]] = {level: [] for level in TARGET_PROMPT_TOKEN_BANDS}
    for row in rows:
        level = row.get("length_level")
        tokens = row.get("prompt_tokens")
        if level in by_level and isinstance(tokens, int):
            by_level[level].append(tokens)
    level_medians = {level: median(values) if values else None for level, values in by_level.items()}
    checks["length_bands"] = all(
        value is not None and bounds[0] <= value <= bounds[1]
        for level, bounds in TARGET_PROMPT_TOKEN_BANDS.items()
        for value in [level_medians[level]]
    )

    lookup = {(r.get("strategy"), r.get("chain_position")): r for r in rows}
    checks["implicit_second_hit"] = (lookup.get(("implicit", 2), {}).get("cached_tokens") or 0) > 0
    checks["explicit_creation_seen"] = (lookup.get(("explicit", 1), {}).get("cache_creation_input_tokens") or 0) > 0
    checks["explicit_second_hit"] = (lookup.get(("explicit", 2), {}).get("cached_tokens") or 0) > 0
    checks["cold_has_no_hit"] = all((r.get("cached_tokens") or 0) == 0 for r in rows if r.get("strategy") == "cold_control")

    return {"pass": all(checks.values()), "checks": checks, "level_prompt_token_medians": level_medians}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    report = {**review(rows), "source_sha256": file_sha256(args.input)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    if not report["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
