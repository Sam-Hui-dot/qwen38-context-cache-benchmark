from __future__ import annotations

import hashlib
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    explicit = [
        PROJECT_ROOT / "README.md",
        PROJECT_ROOT / "requirements.txt",
        PROJECT_ROOT / "preregistration-v1.0.md",
        PROJECT_ROOT / "PREREGISTRATION_V1.1_AMENDMENT.md",
        PROJECT_ROOT / "plans" / "smoke_plan.v1.0.json",
        PROJECT_ROOT / "plans" / "formal_execution_order.v1.0.json",
        PROJECT_ROOT / "data" / "fixtures_manifest.v1.0.json",
        PROJECT_ROOT / "reports" / "OFFICIAL_DOCS_CHECK.md",
    ]
    source_files = sorted((PROJECT_ROOT / "src").glob("*.py"))
    test_files = sorted((PROJECT_ROOT / "tests").glob("*.py"))
    files = sorted(set(explicit + source_files + test_files), key=lambda p: p.as_posix())
    manifest = PROJECT_ROOT / "FREEZE_MANIFEST_V1.1.sha256"
    manifest.write_text(
        "\n".join(f"{sha256_file(path)} *{path.relative_to(PROJECT_ROOT).as_posix()}" for path in files) + "\n",
        encoding="utf-8",
    )
    print(f"files={len(files)} manifest_sha256={sha256_file(manifest)}")


if __name__ == "__main__":
    main()
