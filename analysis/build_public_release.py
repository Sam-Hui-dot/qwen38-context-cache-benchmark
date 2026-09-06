from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]


PUBLIC_FIELDS = [
    "phase", "timestamp", "execution_index", "observation_id", "chain_id",
    "strategy", "length_level", "document_repetition", "chain_position",
    "model", "enable_thinking", "temperature", "max_tokens", "timeout_seconds",
    "fixture_id", "document_sha256", "stable_prefix_sha256", "request_sha256",
    "created", "system_fingerprint", "finish_reason", "final_answer",
    "prompt_tokens", "cached_tokens", "cache_creation_input_tokens",
    "completion_tokens", "reasoning_tokens", "total_tokens", "latency_ms",
    "success", "grader_result", "error_type", "error_message",
]


def copy_file(relative: str, output: Path) -> None:
    source = ROOT / relative
    target = output / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def sanitize_jsonl(source: Path, target: Path) -> None:
    rows = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps({key: row.get(key) for key in PUBLIC_FIELDS}, ensure_ascii=False, separators=(",", ":")) + "\n")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise SystemExit("public output already exists and is not empty")
    output.mkdir(parents=True, exist_ok=True)

    files = [
        "preregistration-v1.0.md",
        "PREREGISTRATION_V1.1_AMENDMENT.md",
        "PREREGISTRATION_V2.0_AMENDMENT.md",
        "FREEZE_MANIFEST_V1.0.sha256",
        "FREEZE_MANIFEST_V1.1.sha256",
        "FREEZE_MANIFEST_V2.0.sha256",
        "requirements.txt",
        "requirements-analysis.txt",
        "pytest.ini",
        "LICENSE",
        "historical/v1-pre-calibration-source.zip",
        "plans/smoke_plan.v1.0.json",
        "plans/formal_execution_order.v1.0.json",
        "data/fixtures_manifest.v1.0.json",
        "data/fixtures_manifest.v2.0.json",
        "reports/OFFICIAL_DOCS_CHECK.md",
        "reports/SMOKE_GATE_PASS.json",
        "reports/FORMAL_GATE_V2.json",
        "reports/FORMAL_REPORT.md",
        "reports/PROTOCOL_AUDIT.md",
        "article_assets/EXPERIMENT_ENVIRONMENT.md",
        "article_assets/RESULTS_FOR_ARTICLE.md",
        "article_assets/MODELSCOPE_DRAFT.md",
        "article_assets/fig01_cache_coverage_cn.png",
        "article_assets/fig02_latency_cn.png",
        "article_assets/fig03_cost_cn.png",
        "article_assets/fig04_execution_heatmap_cn.png",
    ]
    for relative in files:
        copy_file(relative, output)
    for folder in ("src", "tests", "analysis"):
        for source in sorted((ROOT / folder).glob("*.py")):
            copy_file(source.relative_to(ROOT).as_posix(), output)

    sanitize_jsonl(ROOT / "results" / "smoke_test.jsonl", output / "data" / "pilot_smoke_sanitized.jsonl")
    sanitize_jsonl(ROOT / "results" / "formal_results.jsonl", output / "data" / "formal_results_sanitized.jsonl")
    copy_file("results/formal_results_summary.csv", output)
    copy_file("results/protocol_audit.json", output)

    readme = """# Qwen3.8-27B Context Cache Benchmark

本仓库公开一项阿里云百炼 `qwen3.8-27b` 长公共前缀缓存实验：6 次 pilot + 54 次正式请求，对比冷请求基线、隐式缓存和显式缓存。

## 核心结果

- 54/54 正式请求成功且通过确定性评分，0 个 API/transport error。
- 三个服务端实测 Prompt 档位中位数：1,986 / 6,025.5 / 9,987.5 Token。
- 显式缓存 6/6 条链首请求创建、后两次命中；复用覆盖率约 99.2%。
- 显式缓存三请求链的等价输入成本相对匹配冷请求中位减少 51.4%，链总延迟中位减少 41.0%。
- 两条隐式链可能受此前显式链缓存状态影响；原始记录完整保留。无串扰隐式子集只有 4/6 条链，其结果仅作为 post-hoc 敏感性分析。

不要把上述数据解释为模型通用准确率、稳定 SLA 或所有业务场景的缓存收益。

## 本地验证

```powershell
python -m venv .venv
.venv\\Scripts\\python -m pip install -r requirements.txt
.venv\\Scripts\\python -m pytest
```

## 复现实验

自行在仓库根目录创建 `.env`：

```text
DASHSCOPE_API_KEY=your_key_here
BAILIAN_WORKSPACE_ID=your_workspace_id_here
QWEN_CACHE_LIVE_APPROVED=YES
```

仓库不包含任何真实 API Key、Workspace ID 或认证 Header。正式运行会检查已有 observation ID，默认拒绝覆盖；`--resume` 只跳过已记录 ID，不会重发。

运行前请阅读全部 preregistration/amendment。尤其注意：原设计没有为隐式/显式条件设置独立 cache namespace，已在 `reports/PROTOCOL_AUDIT.md` 公开披露。若做新的因果复现，应使用新预注册、不同稳定 namespace 或 TTL washout，不能把新数据混入本次冻结结果。

## 冻结版本核验

`FREEZE_MANIFEST_V2.0.sha256` 对应当前检出的 v2 文件，可直接逐项校验。v1.0/v1.1 清单是预校准历史版本；为避免把历史清单错误地解释为当前文件清单，仓库同时保留 `historical/v1-pre-calibration-source.zip`。解压该归档后，在归档根目录分别校验 v1.0 与 v1.1 清单即可复核当时冻结的全部文件。v2 修订没有覆盖或删除旧清单。

## 数据字段

脱敏 JSONL 保留任务、条件、执行顺序、Token、缓存创建/命中、延迟、答案、确定性评分和错误；移除了原始响应对象、`reasoning_content` 和 response ID。

## 官方文档

- https://help.aliyun.com/zh/model-studio/qwen3-8-27b
- https://help.aliyun.com/zh/model-studio/context-cache

## License

Code and text in this release are provided under the Apache License 2.0.
"""
    (output / "README.md").write_text(readme, encoding="utf-8")
    (output / ".gitignore").write_text(".env\n*.key\n.venv/\n__pycache__/\n.pytest_cache/\n*.pyc\n", encoding="utf-8")
    (output / ".gitattributes").write_text("* text=auto eol=lf\n*.png binary\n*.zip binary\n", encoding="utf-8")
    manifest_files = sorted(path for path in output.rglob("*") if path.is_file() and path.name != "SHA256SUMS")
    (output / "SHA256SUMS").write_text(
        "\n".join(f"{sha256(path)} *{path.relative_to(output).as_posix()}" for path in manifest_files) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": str(output), "files": len(manifest_files) + 1}, ensure_ascii=False))


if __name__ == "__main__":
    main()
