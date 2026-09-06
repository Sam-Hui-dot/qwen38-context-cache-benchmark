from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
from statistics import mean, median
from typing import Any

from src.analysis import equivalent_input_token_cost


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def chain_groups(rows: list[dict[str, Any]]) -> dict[tuple[str, str, int], list[dict[str, Any]]]:
    groups: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    for row in rows:
        key = (row["strategy"], row["length_level"], int(row["document_repetition"]))
        groups.setdefault(key, []).append(row)
    for group in groups.values():
        group.sort(key=lambda row: row["chain_position"])
    return groups


def pct_saving(baseline: float, value: float) -> float:
    return 100 * (baseline - value) / baseline


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--json", type=Path, required=True)
    args = parser.parse_args()

    rows = load_jsonl(args.input)
    groups = chain_groups(rows)
    contaminated: list[dict[str, Any]] = []
    clean_implicit_keys: list[tuple[str, str, int]] = []
    for key, group in groups.items():
        if key[0] != "implicit":
            continue
        first = group[0]
        if (first.get("cached_tokens") or 0) > 0:
            explicit = groups[("explicit", key[1], key[2])]
            contaminated.append(
                {
                    "length_level": key[1],
                    "document_repetition": key[2],
                    "implicit_first_execution": first["execution_index"],
                    "implicit_first_cached_tokens": first["cached_tokens"],
                    "prior_explicit_execution_range": [explicit[0]["execution_index"], explicit[-1]["execution_index"]],
                }
            )
        else:
            clean_implicit_keys.append(key)

    chain_metrics: list[dict[str, Any]] = []
    for strategy in ("implicit", "explicit"):
        for level in ("L1", "L2", "L3"):
            for document in (1, 2):
                key = (strategy, level, document)
                group = groups[key]
                cold = groups[("cold_control", level, document)]
                cost = sum(equivalent_input_token_cost(row) or 0 for row in group)
                cold_cost = sum(equivalent_input_token_cost(row) or 0 for row in cold)
                latency = sum(row["latency_ms"] for row in group)
                cold_latency = sum(row["latency_ms"] for row in cold)
                chain_metrics.append(
                    {
                        "strategy": strategy,
                        "length_level": level,
                        "document_repetition": document,
                        "contaminated": key not in clean_implicit_keys if strategy == "implicit" else False,
                        "cost_saving_pct_vs_cold": pct_saving(cold_cost, cost),
                        "latency_saving_pct_vs_cold": pct_saving(cold_latency, latency),
                        "cached_tokens": sum(row.get("cached_tokens") or 0 for row in group),
                    }
                )

    def selected(strategy: str) -> list[dict[str, Any]]:
        return [
            row for row in chain_metrics
            if row["strategy"] == strategy and (strategy == "explicit" or not row["contaminated"])
        ]

    headline = {}
    for strategy in ("implicit", "explicit"):
        group = selected(strategy)
        headline[strategy] = {
            "chains": len(group),
            "median_chain_cost_saving_pct": median(row["cost_saving_pct_vs_cold"] for row in group),
            "mean_chain_cost_saving_pct": mean(row["cost_saving_pct_vs_cold"] for row in group),
            "median_chain_latency_saving_pct": median(row["latency_saving_pct_vs_cold"] for row in group),
            "mean_chain_latency_saving_pct": mean(row["latency_saving_pct_vs_cold"] for row in group),
        }

    audit = {
        "raw_sha256": sha256(args.input),
        "observations": len(rows),
        "api_errors": sum(row.get("error_type") is not None for row in rows),
        "machine_successes": sum(row.get("success") is True for row in rows),
        "total_tokens": sum(row.get("total_tokens") or 0 for row in rows),
        "contaminated_implicit_chains": contaminated,
        "headline_clean_or_explicit": headline,
        "chain_metrics": chain_metrics,
    }
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Formal protocol audit and post-hoc sensitivity analysis",
        "",
        f"- Raw JSONL SHA-256: `{audit['raw_sha256']}`",
        f"- Formal observations: {len(rows)}",
        f"- API/transport errors: {audit['api_errors']}",
        f"- Deterministic scoring passes: {audit['machine_successes']}/{len(rows)}",
        f"- Formal logical tokens: {audit['total_tokens']:,}",
        "",
        "## Confirmed protocol issue",
        "",
        "Two implicit-cache chains began with non-zero `cached_tokens`. Both matching explicit-cache chains had already run within the same short formal run. Because B and C intentionally used byte-identical prompt text, the later implicit requests may have inherited cache state created by the earlier explicit condition. The design did not isolate cache namespaces or insert a TTL washout. This is condition-order contamination, not an API error.",
        "",
        "| Implicit chain | First execution | First-request cached tokens | Prior explicit executions |",
        "|---|---:|---:|---:|",
    ]
    for item in contaminated:
        lines.append(
            f"| {item['length_level']}-d{item['document_repetition']} | {item['implicit_first_execution']} | "
            f"{item['implicit_first_cached_tokens']:,} | {item['prior_explicit_execution_range'][0]}–{item['prior_explicit_execution_range'][1]} |"
        )
    lines.extend([
        "",
        "No raw record is deleted or rescored. The preregistered all-row summary remains in `FORMAL_REPORT.md`. The following is explicitly post-hoc sensitivity analysis:",
        "",
        f"- Explicit cache: all {headline['explicit']['chains']} chains were internally clean (first request created cache, positions 2/3 hit). Median three-request-chain normalized input-cost saving versus cold control: {headline['explicit']['median_chain_cost_saving_pct']:.1f}%; median latency saving: {headline['explicit']['median_chain_latency_saving_pct']:.1f}%.",
        f"- Implicit cache clean subset: {headline['implicit']['chains']} of 6 chains (12 observations) began cold. Median normalized input-cost saving versus matched cold chains: {headline['implicit']['median_chain_cost_saving_pct']:.1f}%; median latency saving: {headline['implicit']['median_chain_latency_saving_pct']:.1f}%.",
        "- The two contaminated implicit chains remain visible in the raw data but are not used for the clean-subset headline. This subset was not preregistered and must not be presented as the original primary estimate.",
        "",
        "## Interpretation boundary",
        "",
        "The explicit-versus-cold comparison is supported by all six matched chains. The implicit estimate is weaker because only four uncontaminated chains remain. The data do not establish that explicit and implicit cache stores are shared; they only show an order-aligned carryover pattern that requires a separately preregistered follow-up to identify causally.",
    ])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(args.output), "contaminated_chains": len(contaminated)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
