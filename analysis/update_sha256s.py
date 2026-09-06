from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    ignored = {".git", "__pycache__", ".pytest_tmp", ".pytest_cache"}
    files = sorted(
        path for path in root.rglob("*")
        if path.is_file() and path.name != "SHA256SUMS" and not any(part in ignored for part in path.parts)
    )
    lines = [f"{hashlib.sha256(path.read_bytes()).hexdigest()} *{path.relative_to(root).as_posix()}" for path in files]
    (root / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"files={len(files)}")


if __name__ == "__main__":
    main()
