from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re

from dotenv import dotenv_values


TEXT_SUFFIXES = {".md", ".txt", ".json", ".jsonl", ".csv", ".py", ".sha256", ""}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, required=True)
    args = parser.parse_args()
    secrets = dotenv_values(args.env_file)
    key = secrets.get("DASHSCOPE_API_KEY") or ""
    workspace = secrets.get("BAILIAN_WORKSPACE_ID") or ""

    findings = {
        "actual_api_key_files": [],
        "actual_workspace_id_files": [],
        "env_files": [],
        "private_key_like_files": [],
        "windows_absolute_path_files": [],
        "reasoning_content_in_public_data": [],
        "authorization_literal_files": [],
    }
    for path in sorted(args.root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(args.root).as_posix()
        if path.name == ".env" or path.suffix == ".key":
            findings["env_files" if path.name == ".env" else "private_key_like_files"].append(rel)
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if key and key in text:
            findings["actual_api_key_files"].append(rel)
        if workspace and workspace in text:
            findings["actual_workspace_id_files"].append(rel)
        if re.search(r"[A-Za-z]:\\(?:Users|Projects|Windows)\\", text):
            findings["windows_absolute_path_files"].append(rel)
        if rel.startswith("data/") and "reasoning_content" in text:
            findings["reasoning_content_in_public_data"].append(rel)
        if "Authorization" in text:
            findings["authorization_literal_files"].append(rel)

    blocking = sum(
        len(findings[key])
        for key in (
            "actual_api_key_files",
            "actual_workspace_id_files",
            "env_files",
            "private_key_like_files",
            "windows_absolute_path_files",
            "reasoning_content_in_public_data",
        )
    )
    report = {"pass": blocking == 0, "blocking_findings": blocking, "findings": findings}
    print(json.dumps(report, ensure_ascii=False))
    raise SystemExit(0 if report["pass"] else 1)


if __name__ == "__main__":
    main()
