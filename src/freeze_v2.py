from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .fixtures import build_all_fixtures


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    fixture_path = PROJECT_ROOT / "data" / "fixtures_manifest.v2.0.json"
    fixture_path.write_text(
        json.dumps(
            {
                "version": "v2.0",
                "formal_observations_seen_before_freeze": 0,
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
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    explicit = [
        PROJECT_ROOT / "preregistration-v1.0.md",
        PROJECT_ROOT / "PREREGISTRATION_V1.1_AMENDMENT.md",
        PROJECT_ROOT / "PREREGISTRATION_V2.0_AMENDMENT.md",
        PROJECT_ROOT / "FREEZE_MANIFEST_V1.0.sha256",
        PROJECT_ROOT / "FREEZE_MANIFEST_V1.1.sha256",
        PROJECT_ROOT / "plans" / "formal_execution_order.v1.0.json",
        fixture_path,
        PROJECT_ROOT / "reports" / "OFFICIAL_DOCS_CHECK.md",
        PROJECT_ROOT / "reports" / "SMOKE_GATE_PASS.json",
        PROJECT_ROOT / "reports" / "FORMAL_GATE_V2.json",
        PROJECT_ROOT / "requirements.txt",
    ]
    source_files = sorted((PROJECT_ROOT / "src").glob("*.py"))
    test_files = sorted((PROJECT_ROOT / "tests").glob("*.py"))
    files = sorted(set(explicit + source_files + test_files), key=lambda p: p.as_posix())
    manifest = PROJECT_ROOT / "FREEZE_MANIFEST_V2.0.sha256"
    manifest.write_text(
        "\n".join(f"{sha256_file(path)} *{path.relative_to(PROJECT_ROOT).as_posix()}" for path in files) + "\n",
        encoding="utf-8",
    )
    print(f"files={len(files)} manifest_sha256={sha256_file(manifest)}")


if __name__ == "__main__":
    main()
