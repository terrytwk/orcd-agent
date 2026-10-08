from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.sync_docs import sync_docs


ROOT = Path(__file__).resolve().parents[1]
SEARCH = ROOT / "bin" / "orcd-search"
FIXTURES = Path(__file__).parent / "fixtures" / "sample_docs"


def build_index(tmp_path: Path) -> Path:
    output = tmp_path / "orcd_docs.jsonl"
    sync_docs(raw_dir=FIXTURES, output=output, manifest=tmp_path / "manifest.json", skip_download=True)
    return output


def run_search(index: Path, query: str) -> str:
    result = subprocess.run(
        [sys.executable, str(SEARCH), "--index", str(index), query],
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout


def test_miniforge_finds_python_module_docs(tmp_path: Path) -> None:
    output = run_search(build_index(tmp_path), "miniforge")
    assert "Python > Installing Python Packages" in output
    assert "module load miniforge" in output
    assert "https://orcd-docs.mit.edu/python/" in output


def test_gpu_finds_gpu_docs(tmp_path: Path) -> None:
    output = run_search(build_index(tmp_path), "GPU")
    assert "Running Jobs > GPU Jobs" in output
    assert "#SBATCH --gres=gpu:1" in output
    assert "Source:" in output


def test_storage_finds_storage_docs(tmp_path: Path) -> None:
    output = run_search(build_index(tmp_path), "storage")
    assert "Storage > Project Storage" in output
    assert "project storage" in output.lower()
    assert "https://orcd-docs.mit.edu/storage/" in output
