from __future__ import annotations

import argparse
import json
from pathlib import PurePosixPath, Path
import zipfile

from dotenv import dotenv_values


FORBIDDEN_PARTS = {".git", ".venv", "__pycache__", ".pytest_cache", ".pytest_tmp"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, required=True)
    args = parser.parse_args()
    values = dotenv_values(args.env_file)
    secrets = [str(values.get(name) or "").encode("utf-8") for name in ("DASHSCOPE_API_KEY", "BAILIAN_WORKSPACE_ID")]
    secrets = [value for value in secrets if value]
    unsafe_names = []
    secret_files = []
    with zipfile.ZipFile(args.zip) as archive:
        names = archive.namelist()
        for name in names:
            parts = PurePosixPath(name).parts
            if any(part in FORBIDDEN_PARTS for part in parts) or PurePosixPath(name).name == ".env" or PurePosixPath(name).suffix in {".key", ".pyc"}:
                unsafe_names.append(name)
            if not name.endswith("/"):
                data = archive.read(name)
                if any(secret in data for secret in secrets):
                    secret_files.append(name)
    result = {
        "pass": not unsafe_names and not secret_files,
        "entries": len(names),
        "unsafe_entries": unsafe_names,
        "files_containing_actual_secret_values": secret_files,
    }
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(0 if result["pass"] else 1)


if __name__ == "__main__":
    main()
