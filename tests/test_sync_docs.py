from __future__ import annotations

import json
from pathlib import Path

from scripts.sync_docs import parse_markdown, sync_docs


FIXTURES = Path(__file__).parent / "fixtures" / "sample_docs"


def test_parse_markdown_headings_and_code_blocks() -> None:
    records = parse_markdown(FIXTURES / "python.md", FIXTURES, "https://orcd-docs.mit.edu")
    package_section = next(record for record in records if record["section"] == "Installing Python Packages")
    assert package_section["title"] == "Python"
    assert package_section["heading_path"] == ["Python", "Installing Python Packages"]
    assert "module load miniforge" in package_section["code_blocks"][0]
    assert package_section["source_path"] == "python.md"
    assert package_section["url"] == "https://orcd-docs.mit.edu/python/"


def test_sync_docs_generates_jsonl_and_manifest(tmp_path: Path) -> None:
    output = tmp_path / "orcd_docs.jsonl"
    manifest = tmp_path / "manifest.json"
    records, manifest_data = sync_docs(
        raw_dir=FIXTURES,
        output=output,
        manifest=manifest,
        skip_download=True,
    )
    lines = output.read_text(encoding="utf-8").splitlines()
    assert len(lines) == len(records)
    assert all(json.loads(line) for line in lines)
    assert manifest_data["sections"] == len(records)
    assert json.loads(manifest.read_text(encoding="utf-8"))["documents"] == 3


def test_sync_docs_handles_changed_or_new_docs(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    doc = raw_dir / "new.md"
    doc.write_text("# New Doc\n\n## First\n\nOriginal text.\n", encoding="utf-8")
    output = tmp_path / "docs.jsonl"
    manifest = tmp_path / "manifest.json"
    first_records, _ = sync_docs(raw_dir=raw_dir, output=output, manifest=manifest, skip_download=True)
    doc.write_text("# New Doc\n\n## First\n\nChanged text.\n\n## Second\n\nAdded text.\n", encoding="utf-8")
    second_records, _ = sync_docs(raw_dir=raw_dir, output=output, manifest=manifest, skip_download=True)
    assert len(second_records) > len(first_records)
    assert "Changed text" in output.read_text(encoding="utf-8")
