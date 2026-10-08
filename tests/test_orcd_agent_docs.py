from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from scripts.sync_docs import sync_docs


ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "bin" / "orcd-agent"
FIXTURES = Path(__file__).parent / "fixtures" / "sample_docs"


def prepare_home(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    home = tmp_path / "home"
    sync_docs(raw_dir=FIXTURES, knowledge_dir=home / "knowledge", skip_download=True)
    env = os.environ.copy()
    env["ORCD_AGENT_HOME"] = str(home)
    return home, env


def run_docs(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    _, env = prepare_home(tmp_path)
    return subprocess.run(
        [sys.executable, str(AGENT), "docs", *args],
        check=True,
        text=True,
        capture_output=True,
        env=env,
    )


def test_docs_index_prints_index(tmp_path: Path) -> None:
    result = run_docs(tmp_path, "index")
    assert "# MIT ORCD Documentation" in result.stdout
    assert "orcd-agent docs grep" in result.stdout


def test_docs_tree_prints_bounded_markdown_tree(tmp_path: Path) -> None:
    result = run_docs(tmp_path, "tree", "--max-depth", "2")
    assert "software/" in result.stdout
    assert "  python.md" in result.stdout


def test_docs_tree_filters_hidden_and_symlink_entries(tmp_path: Path) -> None:
    home, env = prepare_home(tmp_path)
    knowledge = home / "knowledge"
    (knowledge / ".hidden.md").write_text("# Hidden\n", encoding="utf-8")
    (tmp_path / "external").mkdir()
    (knowledge / "external-link").symlink_to(tmp_path / "external")
    result = subprocess.run(
        [sys.executable, str(AGENT), "docs", "tree"],
        check=True,
        text=True,
        capture_output=True,
        env=env,
    )
    assert ".hidden.md" not in result.stdout
    assert "external-link" not in result.stdout


def test_docs_grep_returns_exact_file_line_matches(tmp_path: Path) -> None:
    result = run_docs(tmp_path, "grep", "miniforge")
    assert "software/python.md:" in result.stdout
    assert "module load miniforge" in result.stdout


def test_docs_grep_uses_fixed_string_matching(tmp_path: Path) -> None:
    _, env = prepare_home(tmp_path)
    result = subprocess.run(
        [sys.executable, str(AGENT), "docs", "grep", "module.*miniforge"],
        text=True,
        capture_output=True,
        env=env,
    )
    assert result.returncode == 1
    assert result.stdout == ""


def test_docs_read_returns_markdown_and_heading(tmp_path: Path) -> None:
    full = run_docs(tmp_path, "read", "software/python.md")
    assert "# Python" in full.stdout
    section = run_docs(tmp_path, "read", "software/python.md", "--heading", "Installing Python Packages")
    assert section.stdout.startswith("## Installing Python Packages")
    assert "module load miniforge" in section.stdout


def test_docs_read_reports_missing_file(tmp_path: Path) -> None:
    _, env = prepare_home(tmp_path)
    result = subprocess.run(
        [sys.executable, str(AGENT), "docs", "read", "missing.md"],
        text=True,
        capture_output=True,
        env=env,
    )
    assert result.returncode == 1
    assert "Documentation file not found" in result.stderr


def test_docs_read_rejects_paths_outside_knowledge(tmp_path: Path) -> None:
    _, env = prepare_home(tmp_path)
    result = subprocess.run(
        [sys.executable, str(AGENT), "docs", "read", "../AGENTS.md"],
        text=True,
        capture_output=True,
        env=env,
    )
    assert result.returncode == 2
    assert "inside the ORCD knowledge directory" in result.stderr


def test_docs_read_rejects_symlink_escape(tmp_path: Path) -> None:
    home, env = prepare_home(tmp_path)
    secret = tmp_path / "secret.md"
    secret.write_text("# Secret\n", encoding="utf-8")
    (home / "knowledge" / "secret-link.md").symlink_to(secret)
    result = subprocess.run(
        [sys.executable, str(AGENT), "docs", "read", "secret-link.md"],
        text=True,
        capture_output=True,
        env=env,
    )
    assert result.returncode == 2
    assert "inside the ORCD knowledge directory" in result.stderr


def test_docs_status_prints_manifest_summary(tmp_path: Path) -> None:
    result = run_docs(tmp_path, "status")
    assert "Source commit:" in result.stdout
    assert "Files:" in result.stdout
