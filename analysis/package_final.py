from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import zipfile


EXCLUDED_PARTS = {".git", ".venv", "__pycache__", ".pytest_cache", ".pytest_tmp"}
EXCLUDED_NAMES = {".env"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output.resolve()
    files = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        if path.name in EXCLUDED_NAMES or path.suffix in {".key", ".pyc"}:
            continue
        files.append(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(files):
            archive.write(path, Path(root.name) / path.relative_to(root))
    print(f"files={len(files)} zip_sha256={sha256(output)}")


if __name__ == "__main__":
    main()
