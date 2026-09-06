from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import median

import matplotlib.pyplot as plt
import numpy as np

from src.analysis import equivalent_input_token_cost


COLORS = {"cold_control": "#6B7280", "implicit": "#2D7DD2", "explicit": "#E45756"}
LABELS = {"cold_control": "冷请求基线", "implicit": "隐式缓存（无串扰子集）", "explicit": "显式缓存"}
LEVEL_LABELS = {"L1": "约 2K", "L2": "约 6K", "L3": "约 10K"}


def load_rows(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def setup_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "Microsoft YaHei",
            "axes.unicode_minus": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "#374151",
            "axes.grid": True,
            "grid.color": "#E5E7EB",
            "grid.linewidth": 0.8,
            "grid.alpha": 0.8,
            "axes.titleweight": "bold",
        }
    )


def groups(rows):
    result = {}
    for row in rows:
        key = (row["strategy"], row["length_level"], int(row["document_repetition"]))
        result.setdefault(key, []).append(row)
    for group in result.values():
        group.sort(key=lambda row: row["chain_position"])
    return result


def is_clean_implicit(group) -> bool:
    return group[0].get("cached_tokens", 0) == 0


def selected_rows(rows, strategy):
    if strategy != "implicit":
        return [row for row in rows if row["strategy"] == strategy]
    result = []
    for key, group in groups(rows).items():
        if key[0] == "implicit" and is_clean_implicit(group):
            result.extend(group)
    return result


def save(fig, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def fig01(rows, output: Path) -> None:
    fig, ax = plt.subplots(figsize=(9.5, 5.4))
    x = np.arange(3)
    width = 0.24
    for offset, strategy in zip((-width, 0, width), ("cold_control", "implicit", "explicit")):
        source = selected_rows(rows, strategy)
        values = []
        for position in (1, 2, 3):
            group = [row for row in source if row["chain_position"] == position]
            values.append(100 * np.mean([(row.get("cached_tokens") or 0) / row["prompt_tokens"] for row in group]))
        bars = ax.bar(x + offset, values, width, label=LABELS[strategy], color=COLORS[strategy])
        ax.bar_label(bars, labels=[f"{v:.1f}%" for v in values], padding=3, fontsize=9)
    ax.set_title("三次连续请求中的缓存覆盖率")
    ax.set_xlabel("缓存链内请求位置")
    ax.set_ylabel("缓存覆盖率（%）")
    ax.set_xticks(x, ["第 1 次（创建/冷）", "第 2 次（复用）", "第 3 次（复用）"])
    ax.set_ylim(0, 110)
    ax.legend(frameon=False, ncol=3, loc="upper left")
    ax.text(0.99, 0.96, "隐式缓存仅含 4 条首请求未命中的链", transform=ax.transAxes, ha="right", va="top", color="#6B7280", fontsize=9)
    save(fig, output)


def fig02(rows, output: Path) -> None:
    fig, ax = plt.subplots(figsize=(9.5, 5.4))
    x = np.arange(3)
    for strategy in ("cold_control", "implicit", "explicit"):
        source = selected_rows(rows, strategy)
        values = [median(row["latency_ms"] for row in source if row["length_level"] == level) for level in ("L1", "L2", "L3")]
        ax.plot(x, values, marker="o", linewidth=2.2, markersize=7, label=LABELS[strategy], color=COLORS[strategy])
        for point_index, (xi, value) in enumerate(zip(x, values)):
            vertical = 10 if strategy != "implicit" else (-17 if point_index == 0 else 10)
            ax.annotate(f"{value/1000:.2f}s", (xi, value), xytext=(0, vertical), textcoords="offset points", ha="center", fontsize=9)
    ax.set_title("不同长前缀下的端到端响应延迟")
    ax.set_xlabel("服务端实测 Prompt 规模")
    ax.set_ylabel("中位延迟（毫秒）")
    ax.set_xticks(x, [LEVEL_LABELS[level] for level in ("L1", "L2", "L3")])
    ax.legend(frameon=False)
    save(fig, output)


def fig03(rows, output: Path) -> None:
    chain_groups = groups(rows)
    ratios = {"cold_control": [100.0] * 6, "implicit": [], "explicit": []}
    for strategy in ("implicit", "explicit"):
        for level in ("L1", "L2", "L3"):
            for document in (1, 2):
                group = chain_groups[(strategy, level, document)]
                if strategy == "implicit" and not is_clean_implicit(group):
                    continue
                cold = chain_groups[("cold_control", level, document)]
                cost = sum(equivalent_input_token_cost(row) or 0 for row in group)
                cold_cost = sum(equivalent_input_token_cost(row) or 0 for row in cold)
                ratios[strategy].append(100 * cost / cold_cost)
    fig, ax = plt.subplots(figsize=(9.2, 5.4))
    strategies = ("cold_control", "implicit", "explicit")
    values = [median(ratios[s]) for s in strategies]
    bars = ax.bar(range(3), values, color=[COLORS[s] for s in strategies], width=0.62)
    ax.bar_label(bars, labels=[f"{v:.1f}%" for v in values], padding=4, fontsize=11)
    for index, strategy in enumerate(strategies):
        jitter = np.linspace(-0.10, 0.10, len(ratios[strategy]))
        ax.scatter(index + jitter, ratios[strategy], color="#111827", s=22, zorder=3, alpha=0.7)
    ax.axhline(100, color="#9CA3AF", linestyle="--", linewidth=1)
    ax.set_title("三次请求链的等价输入成本")
    ax.set_ylabel("相对匹配冷请求链（冷请求 = 100%）")
    ax.set_xticks(range(3), [LABELS[s] for s in strategies])
    ax.set_ylim(0, 115)
    ax.text(0.99, 0.97, "计费权重：未缓存 100%｜显式创建 125%｜显式命中 10%｜隐式命中 20%", transform=ax.transAxes, ha="right", va="top", fontsize=8.5, color="#6B7280")
    save(fig, output)


def fig04(rows, output: Path) -> None:
    chain_groups = groups(rows)
    ordered = sorted(chain_groups.items(), key=lambda item: item[1][0]["execution_index"])
    matrix = []
    labels = []
    contaminated_rows = []
    for row_index, (key, group) in enumerate(ordered):
        strategy, level, document = key
        matrix.append([100 * (row.get("cached_tokens") or 0) / row["prompt_tokens"] for row in group])
        contaminated = strategy == "implicit" and not is_clean_implicit(group)
        if contaminated:
            contaminated_rows.append(row_index)
        suffix = " ＊" if contaminated else ""
        short_label = {"cold_control": "冷请求", "implicit": "隐式", "explicit": "显式"}[strategy]
        labels.append(f"{group[0]['execution_index']:02d}  {short_label} {level}-d{document}{suffix}")
    fig, ax = plt.subplots(figsize=(8.8, 8.2))
    image = ax.imshow(matrix, cmap="Blues", vmin=0, vmax=100, aspect="auto")
    for i in range(len(matrix)):
        for j in range(3):
            value = matrix[i][j]
            ax.text(j, i, f"{value:.0f}%", ha="center", va="center", color="white" if value > 55 else "#111827", fontsize=8)
    for row_index in contaminated_rows:
        ax.add_patch(plt.Rectangle((-0.5, row_index - 0.5), 3, 1, fill=False, edgecolor="#DC2626", linewidth=1.8))
    ax.set_title("18 条缓存链的执行顺序与缓存覆盖率")
    ax.set_xlabel("链内请求位置")
    ax.set_ylabel("首个执行序号 / 策略 / 长度 / 文档")
    ax.set_xticks([0, 1, 2], ["第 1 次", "第 2 次", "第 3 次"])
    ax.set_yticks(range(len(labels)), labels)
    colorbar = fig.colorbar(image, ax=ax, pad=0.02)
    colorbar.set_label("缓存覆盖率")
    ax.text(0.0, -0.08, "＊红框：隐式链首请求已命中，可能受先前显式链缓存状态影响", transform=ax.transAxes, color="#B91C1C", fontsize=9)
    save(fig, output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    setup_style()
    rows = load_rows(args.input)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    fig01(rows, args.output_dir / "fig01_cache_coverage_cn.png")
    fig02(rows, args.output_dir / "fig02_latency_cn.png")
    fig03(rows, args.output_dir / "fig03_cost_cn.png")
    fig04(rows, args.output_dir / "fig04_execution_heatmap_cn.png")
    print(json.dumps({"figures": 4, "output_dir": str(args.output_dir)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
