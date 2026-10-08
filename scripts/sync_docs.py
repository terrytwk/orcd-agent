#!/usr/bin/env python3
"""Synchronize public ORCD Markdown docs into a local JSONL search index."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from dataclasses import dataclass, field
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPO = os.environ.get("ORCD_DOCS_REPO", "https://github.com/mit-orcd/orcd-docs-edit.git")
DEFAULT_BRANCH = os.environ.get("ORCD_DOCS_BRANCH", "main")
DEFAULT_BASE_URL = os.environ.get("ORCD_DOCS_BASE_URL", "https://orcd-docs.mit.edu")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
FENCE_RE = re.compile(r"^(```|~~~)")


@dataclass
class Section:
    title: str
    section: str
    heading_path: list[str]
    source_path: str
    url: str
    text_lines: list[str] = field(default_factory=list)
    code_blocks: list[str] = field(default_factory=list)

    def to_record(self) -> dict:
        return {
            "title": self.title,
            "section": self.section,
            "heading_path": self.heading_path,
            "source_path": self.source_path,
            "url": self.url,
            "text": "\n".join(self.text_lines).strip(),
            "code_blocks": self.code_blocks,
        }


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^\w\s/-]", "", value)
    value = re.sub(r"\s+", "-", value)
    return value


def source_url(source_path: str, base_url: str) -> str:
    path = Path(source_path)
    parts = list(path.with_suffix("").parts)
    if parts and parts[-1].lower() == "index":
        parts = parts[:-1]
    if parts and parts[0] in {"docs", "src"}:
        parts = parts[1:]
    web_path = "/".join(slugify(part) for part in parts if part)
    base = base_url.rstrip("/")
    return f"{base}/{web_path}/" if web_path else f"{base}/"


def clean_heading(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("`", "")).strip()


def discover_markdown_files(root: Path) -> list[Path]:
    ignored = {".git", ".github", "node_modules", "site", "_site", "public"}
    files = []
    for path in root.rglob("*.md"):
        if any(part in ignored for part in path.parts):
            continue
        files.append(path)
    return sorted(files)


def parse_markdown(path: Path, source_root: Path, base_url: str) -> list[dict]:
    rel = path.relative_to(source_root).as_posix()
    url = source_url(rel, base_url)
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    title = path.stem.replace("-", " ").replace("_", " ").title()
    headings: list[tuple[int, str]] = []
    sections: list[Section] = []
    current: Section | None = None
    in_code = False
    code_buffer: list[str] = []

    def finish_current() -> None:
        nonlocal current
        if current and (current.text_lines or current.code_blocks):
            sections.append(current)
        current = None

    for line in lines:
        if FENCE_RE.match(line.strip()):
            if in_code:
                in_code = False
                if current is None:
                    current = Section(title, title, [title], rel, url)
                current.code_blocks.append("\n".join(code_buffer).strip())
                current.text_lines.append(line)
                code_buffer = []
            else:
                in_code = True
                if current is None:
                    current = Section(title, title, [title], rel, url)
                current.text_lines.append(line)
            continue

        if in_code:
            code_buffer.append(line)
            if current is not None:
                current.text_lines.append(line)
            continue

        match = HEADING_RE.match(line)
        if match:
            finish_current()
            level = len(match.group(1))
            heading_text = clean_heading(match.group(2))
            headings = [(lvl, text) for lvl, text in headings if lvl < level]
            headings.append((level, heading_text))
            if level == 1:
                title = heading_text
            path_headings = [text for _, text in headings]
            section_name = path_headings[-1] if path_headings else title
            current = Section(title, section_name, path_headings, rel, url)
            current.text_lines.append(line)
            continue

        if current is None:
            current = Section(title, title, [title], rel, url)
        current.text_lines.append(line)

    if in_code and current is not None and code_buffer:
        current.code_blocks.append("\n".join(code_buffer).strip())
    finish_current()
    return [section.to_record() for section in sections if section.to_record()["text"]]


def run_git(args: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def download_zip(repo_url: str, branch: str, destination: Path) -> str:
    if not repo_url.startswith("https://github.com/"):
        raise RuntimeError("zip fallback supports GitHub HTTPS repositories only")
    owner_repo = repo_url.removeprefix("https://github.com/").removesuffix(".git")
    archive_url = f"https://github.com/{owner_repo}/archive/refs/heads/{branch}.zip"
    with tempfile.TemporaryDirectory(prefix="orcd-docs-zip-") as tmp:
        zip_path = Path(tmp) / "docs.zip"
        urllib.request.urlretrieve(archive_url, zip_path)
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(tmp)
        extracted = next(path for path in Path(tmp).iterdir() if path.is_dir())
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(extracted, destination)
    return f"zip:{branch}"


def sync_source(repo_url: str, branch: str, raw_dir: Path) -> str:
    raw_dir.parent.mkdir(parents=True, exist_ok=True)
    if shutil.which("git"):
        try:
            if (raw_dir / ".git").exists():
                current_origin = run_git(["remote", "get-url", "origin"], raw_dir)
                if current_origin != repo_url:
                    shutil.rmtree(raw_dir)
                    run_git(["clone", "--depth", "1", "--branch", branch, repo_url, str(raw_dir)])
                    return run_git(["rev-parse", "HEAD"], raw_dir)
                run_git(["fetch", "--depth", "1", "origin", branch], raw_dir)
                run_git(["checkout", "FETCH_HEAD"], raw_dir)
            else:
                if raw_dir.exists():
                    shutil.rmtree(raw_dir)
                run_git(["clone", "--depth", "1", "--branch", branch, repo_url, str(raw_dir)])
            return run_git(["rev-parse", "HEAD"], raw_dir)
        except subprocess.CalledProcessError as exc:
            print(f"git sync failed, trying zip download: {exc.stderr.strip()}", file=sys.stderr)
    return download_zip(repo_url, branch, raw_dir)


def write_jsonl(records: list[dict], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def sync_docs(
    repo_url: str = DEFAULT_REPO,
    branch: str = DEFAULT_BRANCH,
    base_url: str = DEFAULT_BASE_URL,
    raw_dir: Path = ROOT / "docs" / "raw" / "orcd-docs",
    output: Path = ROOT / "docs" / "processed" / "orcd_docs.jsonl",
    manifest: Path = ROOT / "docs" / "manifest.json",
    skip_download: bool = False,
) -> tuple[list[dict], dict]:
    commit = "local"
    if not skip_download:
        commit = sync_source(repo_url, branch, raw_dir)
    markdown_files = discover_markdown_files(raw_dir)
    records: list[dict] = []
    for path in markdown_files:
        records.extend(parse_markdown(path, raw_dir, base_url))
    write_jsonl(records, output)
    manifest_data = {
        "source_repo": repo_url,
        "source_branch": branch,
        "source_commit": commit,
        "base_url": base_url,
        "synced_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "documents": len(markdown_files),
        "sections": len(records),
        "output": output.relative_to(ROOT).as_posix() if output.is_relative_to(ROOT) else str(output),
    }
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(manifest_data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return records, manifest_data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Synchronize ORCD docs into a local JSONL index.")
    parser.add_argument("--repo", default=DEFAULT_REPO, help="ORCD docs git repository URL.")
    parser.add_argument("--branch", default=DEFAULT_BRANCH, help="Docs repository branch.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Rendered docs base URL.")
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "docs" / "raw" / "orcd-docs")
    parser.add_argument("--output", type=Path, default=ROOT / "docs" / "processed" / "orcd_docs.jsonl")
    parser.add_argument("--manifest", type=Path, default=ROOT / "docs" / "manifest.json")
    parser.add_argument("--skip-download", action="store_true", help="Index existing --raw-dir content.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    records, manifest = sync_docs(
        repo_url=args.repo,
        branch=args.branch,
        base_url=args.base_url,
        raw_dir=args.raw_dir,
        output=args.output,
        manifest=args.manifest,
        skip_download=args.skip_download,
    )
    print(f"Indexed {len(records)} ORCD documentation sections.")
    print(f"Manifest: {args.manifest}")
    print(f"Source version: {manifest['source_commit']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
