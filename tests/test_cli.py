from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_cli_compile_validate_diff(tmp_path: Path) -> None:
    input_path = ROOT / "spec" / "examples" / "pipespec" / "pm25_alert_pipeline.json"
    out_path = tmp_path / "out.json"

    compile_cmd = [
        sys.executable,
        "-m",
        "orchspec_validator.cli.compile",
        str(input_path),
        "--out",
        str(out_path),
        "--format",
        "json",
        "--strict",
    ]
    r1 = subprocess.run(compile_cmd, cwd=ROOT, capture_output=True, text=True)
    assert r1.returncode == 0, r1.stderr

    validate_cmd = [
        sys.executable,
        "-m",
        "orchspec_validator.cli.validate",
        str(out_path),
        "--json-report",
    ]
    r2 = subprocess.run(validate_cmd, cwd=ROOT, capture_output=True, text=True)
    assert r2.returncode == 0, r2.stderr
    payload = json.loads(r2.stdout)
    assert payload["summary"]["valid"] is True

    diff_cmd = [
        sys.executable,
        "-m",
        "orchspec_validator.cli.diff",
        str(out_path),
        str(out_path),
        "--json-report",
    ]
    r3 = subprocess.run(diff_cmd, cwd=ROOT, capture_output=True, text=True)
    assert r3.returncode == 0, r3.stderr
    diff_payload = json.loads(r3.stdout)
    assert diff_payload["changes"] == []
