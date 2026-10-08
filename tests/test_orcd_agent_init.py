from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "bin" / "orcd-agent"


def run_agent(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(AGENT), *args],
        cwd=tmp_path,
        check=True,
        text=True,
        capture_output=True,
        env=os.environ.copy(),
    )


def test_init_creates_orcd_file_and_reference_agents_when_missing(tmp_path: Path) -> None:
    result = run_agent(tmp_path, "init")
    agents = tmp_path / "AGENTS.md"
    orcd_agents = tmp_path / ".orcd" / "AGENTS_ORCD.md"
    assert agents.exists()
    assert orcd_agents.exists()
    assert ".orcd/AGENTS_ORCD.md" in agents.read_text(encoding="utf-8")
    assert "Never run expensive computation on login nodes" in orcd_agents.read_text(encoding="utf-8")
    assert "Created" in result.stdout


def test_init_never_overwrites_existing_agents_by_default(tmp_path: Path) -> None:
    agents = tmp_path / "AGENTS.md"
    original = "# Project Rules\n\nKeep repo conventions first.\n"
    agents.write_text(original, encoding="utf-8")
    result = run_agent(tmp_path, "init")
    assert agents.read_text(encoding="utf-8") == original
    assert (tmp_path / ".orcd" / "AGENTS_ORCD.md").exists()
    assert "Left existing" in result.stdout
    assert "authoritative" in result.stdout


def test_init_appends_reference_only_with_explicit_flag(tmp_path: Path) -> None:
    agents = tmp_path / "AGENTS.md"
    original = "# Project Rules\n\nKeep repo conventions first.\n"
    agents.write_text(original, encoding="utf-8")
    run_agent(tmp_path, "init", "--append-reference")
    updated = agents.read_text(encoding="utf-8")
    assert updated.startswith(original)
    assert "## ORCD / HPC context" in updated
    assert ".orcd/AGENTS_ORCD.md" in updated
    assert "Never run expensive computation on login nodes" not in updated


def test_context_json_subcommand() -> None:
    result = subprocess.run(
        [sys.executable, str(AGENT), "context", "--json"],
        check=True,
        text=True,
        capture_output=True,
    )
    payload = json.loads(result.stdout)
    assert "node_type" in payload
    assert "current_directory" in payload
