from __future__ import annotations

import json
from pathlib import Path

from scripts.sync_docs import find_canonical_markdown_root, sync_docs


FIXTURES = Path(__file__).parent / "fixtures" / "sample_docs"


def test_find_canonical_markdown_root_prefers_docs_directory(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    (raw_dir / "docs" / "software").mkdir(parents=True)
    (raw_dir / "docs" / "software" / "python.md").write_text("# Python\n", encoding="utf-8")
    (raw_dir / "README.md").write_text("# Repo Readme\n", encoding="utf-8")
    assert find_canonical_markdown_root(raw_dir) == raw_dir / "docs"


def test_sync_docs_copies_markdown_tree_and_generates_metadata(tmp_path: Path) -> None:
    knowledge_dir = tmp_path / "knowledge"
    copied, manifest_data = sync_docs(
        raw_dir=FIXTURES,
        knowledge_dir=knowledge_dir,
        skip_download=True,
    )
    assert Path("software/python.md") in copied
    assert (knowledge_dir / "software" / "python.md").exists()
    assert "module load miniforge" in (knowledge_dir / "software" / "python.md").read_text(encoding="utf-8")
    assert "# MIT ORCD Documentation" in (knowledge_dir / "INDEX.md").read_text(encoding="utf-8")
    manifest = json.loads((knowledge_dir / ".manifest.json").read_text(encoding="utf-8"))
    assert manifest["documents"] == len(copied)
    assert manifest["file_count"] == len(copied)
    assert manifest["source"] == "mit-orcd/orcd-docs-edit"
    assert manifest_data["knowledge_dir"] == str(knowledge_dir)


def test_sync_docs_replaces_old_corpus_after_successful_sync(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    (raw_dir / "docs").mkdir(parents=True)
    doc = raw_dir / "docs" / "new.md"
    doc.write_text("# New Doc\n\nOriginal text.\n", encoding="utf-8")
    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir()
    (knowledge_dir / "stale.md").write_text("stale", encoding="utf-8")
    sync_docs(raw_dir=raw_dir, knowledge_dir=knowledge_dir, skip_download=True)
    assert not (knowledge_dir / "stale.md").exists()
    assert "Original text" in (knowledge_dir / "new.md").read_text(encoding="utf-8")
    doc.write_text("# New Doc\n\nChanged text.\n", encoding="utf-8")
    sync_docs(raw_dir=raw_dir, knowledge_dir=knowledge_dir, skip_download=True)
    assert "Changed text" in (knowledge_dir / "new.md").read_text(encoding="utf-8")


def test_sync_docs_does_not_copy_build_artifacts(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    (raw_dir / "docs").mkdir(parents=True)
    (raw_dir / "docs" / "page.md").write_text("# Page\n", encoding="utf-8")
    (raw_dir / "docs" / "index.html").write_text("<html></html>", encoding="utf-8")
    knowledge_dir = tmp_path / "knowledge"
    sync_docs(raw_dir=raw_dir, knowledge_dir=knowledge_dir, skip_download=True)
    assert (knowledge_dir / "page.md").exists()
    assert not (knowledge_dir / "index.html").exists()


def test_sync_failure_preserves_previous_good_corpus(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    (raw_dir / "docs").mkdir(parents=True)
    (raw_dir / "docs" / "good.md").write_text("# Good\n", encoding="utf-8")
    knowledge_dir = tmp_path / "knowledge"
    sync_docs(raw_dir=raw_dir, knowledge_dir=knowledge_dir, skip_download=True)
    try:
        sync_docs(raw_dir=tmp_path / "missing", knowledge_dir=knowledge_dir, skip_download=True)
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("missing source should fail")
    assert (knowledge_dir / "good.md").read_text(encoding="utf-8") == "# Good\n"
