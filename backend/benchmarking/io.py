from __future__ import annotations

import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def environment_metadata(notes: str, command: str) -> dict:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            check=True,
            text=True,
            timeout=5,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        commit = "unknown"
    return {
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": commit,
        "operating_system": platform.platform(),
        "python_version": sys.version.split()[0],
        "notes": notes,
        "command": command,
    }


def load_fixtures(directory: Path) -> tuple[list[dict], dict]:
    manifest_path = directory / "manifest.json"
    if not manifest_path.exists():
        generator = Path(__file__).resolve().parents[2] / "scripts" / "generate_privacy_benchmark_fixtures.py"
        subprocess.run(
            [sys.executable, str(generator), "--profile", "full", "--output", str(directory)],
            check=True,
            timeout=180,
        )
    if not manifest_path.exists():
        raise FileNotFoundError(f"Fixture generation did not create {manifest_path}.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    fixtures = [
        {**item, "path": directory / item["filename"]}
        for item in manifest["fixtures"]
        if not item["intentionally_invalid"]
    ]
    if not fixtures or any(not item["path"].exists() for item in fixtures):
        raise RuntimeError("Fixture manifest contains no usable files or references missing files.")
    return fixtures, manifest


def write_result_bundle(
    output: Path,
    raw: list[dict],
    summary: dict,
    environment: dict,
    fixture_manifest: dict | None = None,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps({
            "summary": summary,
            "environment": environment,
            "fixture_manifest": fixture_manifest,
            "samples": raw,
        }, indent=2)
        + "\n",
        encoding="utf-8",
    )
