from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .execution_plan import build_execution_plan
from .fixtures import build_all_fixtures
from .smoke_plan import build_smoke_plan


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=20260906)
    args = parser.parse_args()

    draft_path = PROJECT_ROOT / "DRAFT_PREREGISTRATION.md"
    frozen_path = PROJECT_ROOT / "preregistration-v1.0.md"
    frozen_text = draft_path.read_text(encoding="utf-8")
    frozen_text = frozen_text.replace(
        "# Draft preregistration: Qwen3.8-27B context-cache benchmark",
        "# Preregistration v1.0: Qwen3.8-27B context-cache benchmark",
        1,
    ).replace(
        "状态：**DRAFT / NOT FROZEN / NO LIVE OUTPUT OBSERVED**",
        "状态：**FROZEN v1.0 / NO LIVE OUTPUT OBSERVED BEFORE FREEZE**",
        1,
    ).replace(
        "本文件用于人工审计，不构成冻结版本。任何真实 API 调用前必须另存正式 preregistration、生成 SHA-256，并锁定执行顺序。",
        "本版本在任何真实 API 输出被观察前冻结。后续修订必须新增版本和理由，不覆盖本文件或原始 SHA-256。",
        1,
    )
    frozen_path.write_text(frozen_text, encoding="utf-8")

    smoke_path = PROJECT_ROOT / "plans" / "smoke_plan.v1.0.json"
    formal_path = PROJECT_ROOT / "plans" / "formal_execution_order.v1.0.json"
    fixture_path = PROJECT_ROOT / "data" / "fixtures_manifest.v1.0.json"
    write_json(smoke_path, build_smoke_plan())
    write_json(formal_path, build_execution_plan(args.seed))
    write_json(
        fixture_path,
        {
            "version": "v1.0",
            "fixtures": [
                {
                    "fixture_id": fixture.fixture_id,
                    "level": fixture.level,
                    "seed": fixture.seed,
                    "character_count": len(fixture.text),
                    "utf8_byte_count": len(fixture.text.encode("utf-8")),
                    "document_sha256": fixture.sha256,
                    "questions": list(fixture.questions),
                    "gold": [
                        {"answer": answer.answer, "evidence_id": answer.evidence_id}
                        for answer in fixture.gold
                    ],
                }
                for fixture in build_all_fixtures()
            ],
        },
    )

    frozen_files = [
        frozen_path,
        smoke_path,
        formal_path,
        fixture_path,
        PROJECT_ROOT / "src" / "constants.py",
        PROJECT_ROOT / "src" / "fixtures.py",
        PROJECT_ROOT / "src" / "request_builder.py",
        PROJECT_ROOT / "src" / "scoring.py",
        PROJECT_ROOT / "src" / "runner.py",
        PROJECT_ROOT / "src" / "review_smoke.py",
        PROJECT_ROOT / "src" / "analysis.py",
        PROJECT_ROOT / "reports" / "OFFICIAL_DOCS_CHECK.md",
    ]
    manifest_path = PROJECT_ROOT / "FREEZE_MANIFEST_V1.0.sha256"
    lines = [f"{sha256_file(path)} *{path.relative_to(PROJECT_ROOT).as_posix()}" for path in frozen_files]
    manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "version": "v1.0",
                "seed": args.seed,
                "frozen_files": len(frozen_files),
                "manifest_sha256": sha256_file(manifest_path),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
