from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable


def _numbers(rows: Iterable[dict[str, Any]], key: str) -> list[float]:
    return [float(row[key]) for row in rows if isinstance(row.get(key), (int, float))]


def p95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]


def equivalent_input_token_cost(row: dict[str, Any]) -> float | None:
    """Normalized input cost using documented cache multipliers.

    One uncached input token is one unit. Explicit creation is 1.25 units,
    explicit hits 0.10 units, and implicit hits 0.20 units. Output cost is not
    included and must be reported separately.
    """
    prompt = row.get("prompt_tokens")
    if not isinstance(prompt, int):
        return None
    cached = row.get("cached_tokens") or 0
    created = row.get("cache_creation_input_tokens") or 0
    uncached = max(0, prompt - cached - created)
    strategy = row.get("strategy")
    if strategy == "explicit":
        return uncached + 1.25 * created + 0.10 * cached
    if strategy == "implicit":
        return uncached + 0.20 * cached
    return float(prompt)


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for strategy in ("cold_control", "implicit", "explicit"):
        group = [row for row in rows if row.get("strategy") == strategy]
        valid = [row for row in group if row.get("error_type") is None]
        latencies = _numbers(valid, "latency_ms")
        prompts = _numbers(valid, "prompt_tokens")
        cached = _numbers(valid, "cached_tokens")
        costs = [value for row in valid if (value := equivalent_input_token_cost(row)) is not None]
        summary[strategy] = {
            "observations": len(group),
            "api_errors": len(group) - len(valid),
            "machine_successes": sum(row.get("success") is True for row in group),
            "cache_hit_observations": sum((row.get("cached_tokens") or 0) > 0 for row in valid),
            "mean_prompt_tokens": mean(prompts) if prompts else None,
            "median_prompt_tokens": median(prompts) if prompts else None,
            "total_prompt_tokens": sum(prompts),
            "total_cached_tokens": sum(cached),
            "mean_latency_ms": mean(latencies) if latencies else None,
            "median_latency_ms": median(latencies) if latencies else None,
            "p95_latency_ms": p95(latencies),
            "total_equivalent_input_token_cost": sum(costs),
        }
    return summary


def matched_deltas(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    index = {
        (
            row.get("strategy"),
            row.get("length_level"),
            row.get("document_repetition"),
            row.get("chain_position"),
        ): row
        for row in rows
    }
    deltas = []
    for level in ("L1", "L2", "L3"):
        for document in (1, 2):
            for position in (1, 2, 3):
                cold = index.get(("cold_control", level, document, position))
                if not cold or cold.get("error_type") is not None:
                    continue
                cold_cost = equivalent_input_token_cost(cold)
                for strategy in ("implicit", "explicit"):
                    other = index.get((strategy, level, document, position))
                    if not other or other.get("error_type") is not None:
                        continue
                    other_cost = equivalent_input_token_cost(other)
                    if cold_cost is None or other_cost is None:
                        continue
                    deltas.append(
                        {
                            "strategy": strategy,
                            "length_level": level,
                            "document_repetition": document,
                            "chain_position": position,
                            "latency_delta_ms_vs_cold": other["latency_ms"] - cold["latency_ms"],
                            "equivalent_input_cost_delta_vs_cold": other_cost - cold_cost,
                            "equivalent_input_cost_saving_pct": 100 * (cold_cost - other_cost) / cold_cost if cold_cost else None,
                            "cached_tokens": other.get("cached_tokens"),
                            "both_machine_success": cold.get("success") is True and other.get("success") is True,
                        }
                    )
    return deltas


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    columns = [
        "execution_index", "observation_id", "strategy", "length_level",
        "document_repetition", "chain_position", "success", "error_type",
        "latency_ms", "prompt_tokens", "cached_tokens",
        "cache_creation_input_tokens", "completion_tokens", "total_tokens",
        "equivalent_input_token_cost", "response_id", "finish_reason",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            flat = {key: row.get(key) for key in columns}
            flat["equivalent_input_token_cost"] = equivalent_input_token_cost(row)
            writer.writerow(flat)


def _fmt(value: Any, digits: int = 1) -> str:
    return "NA" if value is None else f"{value:,.{digits}f}"


def write_report(rows: list[dict[str, Any]], path: Path) -> None:
    summary = summarize(rows)
    deltas = matched_deltas(rows)
    total_tokens = sum(row.get("total_tokens") or 0 for row in rows)
    lines = [
        "# Qwen3.8-27B Context Cache Formal Report",
        "",
        f"- Observations: {len(rows)}",
        f"- API/transport errors: {sum(row.get('error_type') is not None for row in rows)}",
        f"- Machine-scored successes: {sum(row.get('success') is True for row in rows)}",
        f"- Total logical tokens: {total_tokens:,}",
        "",
        "## Strategy summary",
        "",
        "| Strategy | N | Errors | Correct | Cache-hit obs | Prompt total | Cached total | Median latency ms | P95 latency ms | Equivalent input cost |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for strategy, item in summary.items():
        lines.append(
            f"| {strategy} | {item['observations']} | {item['api_errors']} | "
            f"{item['machine_successes']} | {item['cache_hit_observations']} | "
            f"{_fmt(item['total_prompt_tokens'], 0)} | {_fmt(item['total_cached_tokens'], 0)} | "
            f"{_fmt(item['median_latency_ms'])} | {_fmt(item['p95_latency_ms'])} | "
            f"{_fmt(item['total_equivalent_input_token_cost'])} |"
        )
    lines.extend([
        "",
        "Equivalent input cost uses normalized multipliers: uncached=1.00, explicit creation=1.25, explicit hit=0.10, implicit hit=0.20. Output-token cost is excluded.",
        "",
        "## Matched comparison against cold control",
        "",
    ])
    for strategy in ("implicit", "explicit"):
        group = [row for row in deltas if row["strategy"] == strategy]
        latency = _numbers(group, "latency_delta_ms_vs_cold")
        savings = _numbers(group, "equivalent_input_cost_saving_pct")
        lines.append(
            f"- {strategy}: matched pairs={len(group)}, median latency delta={_fmt(median(latency) if latency else None)} ms, "
            f"median equivalent input-cost saving={_fmt(median(savings) if savings else None)}%."
        )
    failures = [row for row in rows if row.get("error_type") or row.get("success") is not True]
    lines.extend(["", "## Failures", ""])
    if not failures:
        lines.append("No API, transport, parse, or machine-scoring failures.")
    else:
        for row in failures:
            lines.append(
                f"- `{row.get('observation_id')}`: error={row.get('error_type')}, "
                f"grader={json.dumps(row.get('grader_result'), ensure_ascii=False)}"
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    write_csv(rows, args.csv)
    write_report(rows, args.report)
    print(json.dumps({"observations": len(rows), "csv": str(args.csv), "report": str(args.report)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
