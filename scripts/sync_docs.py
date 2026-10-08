#!/usr/bin/env python3
"""Synchronize public ORCD Markdown docs into a local knowledge tree."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path


DEFAULT_REPO = os.environ.get("ORCD_DOCS_REPO", "https://github.com/mit-orcd/orcd-docs-edit.git")
DEFAULT_BRANCH = os.environ.get("ORCD_DOCS_BRANCH", "main")
DEFAULT_BASE_URL = os.environ.get("ORCD_DOCS_BASE_URL", "https://orcd-docs.mit.edu")


def agent_home() -> Path:
    return Path(os.environ.get("ORCD_AGENT_HOME", "~/.orcd-agent")).expanduser()


def default_raw_dir() -> Path:
    return agent_home() / "cache" / "orcd-docs"


def default_knowledge_dir() -> Path:
    return agent_home() / "knowledge"


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


def markdown_files(root: Path) -> list[Path]:
    ignored_parts = {".git", ".github", "node_modules", "site", "_site", "public", "__pycache__", "images"}
    return sorted(
        path
        for path in root.rglob("*.md")
        if path.is_file() and not any(part in ignored_parts for part in path.parts)
    )


def find_canonical_markdown_root(source_root: Path) -> Path:
    docs_root = source_root / "docs"
    if docs_root.is_dir() and markdown_files(docs_root):
        return docs_root
    candidates = [path for path in source_root.iterdir() if path.is_dir() and path.name not in {".git", ".github"}]
    candidates.append(source_root)
    return max(candidates, key=lambda path: len(markdown_files(path)))


def title_for(path_name: str) -> str:
    special = {
        "orcd": "ORCD",
        "hpc": "HPC",
        "gpu": "GPU",
        "gpus": "GPUs",
        "ssh": "SSH",
        "x11": "X11",
    }
    words = path_name.replace("_", "-").split("-")
    return " ".join(special.get(word.lower(), word.capitalize()) for word in words)


def top_level_entries(markdown_root: Path) -> list[tuple[str, Path]]:
    entries = [(path.name, path) for path in markdown_root.iterdir() if path.is_dir() and markdown_files(path)]
    return sorted(entries, key=lambda item: item[0])


def generate_index(markdown_root: Path, copied_files: list[Path]) -> str:
    topic_covers = {
        "accessing-orcd": ["SSH login", "OnDemand", "control channels", "troubleshooting access"],
        "filesystems-file-transfer": ["home", "pool", "scratch", "file transfer", "Lustre best practices"],
        "recipes": ["common workflows", "application examples", "Jupyter", "VS Code", "GPU examples"],
        "running-jobs": ["Slurm", "batch jobs", "interactive jobs", "resource requests", "GPUs", "monitoring", "job arrays"],
        "services": ["compute services", "storage rental", "hosted hardware", "group access"],
        "software": ["modules", "Python", "Miniforge", "environments", "compiling software", "containers"],
    }
    lines = [
        "# MIT ORCD Documentation",
        "",
        "Canonical local Markdown copied from the public ORCD documentation source.",
        "",
    ]
    for name, _ in top_level_entries(markdown_root):
        lines.extend([f"## {title_for(name)}", f"Path: `{name}/`", "", "Covers:"])
        for item in topic_covers.get(name, ["ORCD documentation pages in this section"]):
            lines.append(f"- {item}")
        lines.append("")
    top_level_docs = sorted(path.name for path in copied_files if len(path.parts) == 1 and path.name != "INDEX.md")
    if top_level_docs:
        lines.extend(["## Top-Level Pages", "", "Useful standalone pages:"])
        for name in top_level_docs[:12]:
            lines.append(f"- `{name}`")
        lines.append("")
    lines.extend(
        [
            "## How To Use",
            "",
            "- Inspect this map with `orcd-agent docs index`.",
            "- Browse paths with `orcd-agent docs tree`.",
            "- Search exact terms with `orcd-agent docs grep \"<term>\"`.",
            "- Read full Markdown files with `orcd-agent docs read <path>`.",
            "",
        ]
    )
    return "\n".join(lines)


def copy_markdown_tree(markdown_root: Path, destination: Path) -> list[Path]:
    copied: list[Path] = []
    for source in markdown_files(markdown_root):
        relative = source.relative_to(markdown_root)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append(relative)
    return copied


def atomic_replace(source_dir: Path, target_dir: Path) -> None:
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    backup_dir = target_dir.with_name(f".{target_dir.name}.previous")
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    if target_dir.exists():
        target_dir.rename(backup_dir)
    source_dir.rename(target_dir)
    if backup_dir.exists():
        shutil.rmtree(backup_dir)


def sync_docs(
    repo_url: str = DEFAULT_REPO,
    branch: str = DEFAULT_BRANCH,
    base_url: str = DEFAULT_BASE_URL,
    raw_dir: Path | None = None,
    knowledge_dir: Path | None = None,
    skip_download: bool = False,
) -> tuple[list[Path], dict]:
    raw_dir = raw_dir or default_raw_dir()
    knowledge_dir = knowledge_dir or default_knowledge_dir()
    commit = "local"
    if not skip_download:
        commit = sync_source(repo_url, branch, raw_dir)

    markdown_root = find_canonical_markdown_root(raw_dir)
    staging_parent = knowledge_dir.parent
    staging_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".knowledge-sync-", dir=staging_parent) as tmp:
        staging = Path(tmp) / "knowledge"
        staging.mkdir()
        copied = copy_markdown_tree(markdown_root, staging)
        (staging / "INDEX.md").write_text(generate_index(markdown_root, copied), encoding="utf-8")
        manifest_data = {
            "source": repo_url.removeprefix("https://github.com/").removesuffix(".git"),
            "source_repo": repo_url,
            "source_branch": branch,
            "commit": commit,
            "source_commit": commit,
            "source_markdown_root": str(markdown_root),
            "base_url": base_url,
            "synced_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "file_count": len(copied),
            "documents": len(copied),
            "knowledge_dir": str(knowledge_dir),
        }
        (staging / ".manifest.json").write_text(
            json.dumps(manifest_data, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        atomic_replace(staging, knowledge_dir)
    return copied, manifest_data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Synchronize ORCD docs into a local Markdown knowledge tree.")
    parser.add_argument("--repo", default=DEFAULT_REPO, help="ORCD docs git repository URL.")
    parser.add_argument("--branch", default=DEFAULT_BRANCH, help="Docs repository branch.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Rendered docs base URL for manifest metadata.")
    parser.add_argument("--raw-dir", type=Path, default=None, help="Source checkout/cache directory.")
    parser.add_argument("--knowledge-dir", type=Path, default=None, help="Destination knowledge directory.")
    parser.add_argument("--skip-download", action="store_true", help="Copy existing --raw-dir content.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    copied, manifest = sync_docs(
        repo_url=args.repo,
        branch=args.branch,
        base_url=args.base_url,
        raw_dir=args.raw_dir,
        knowledge_dir=args.knowledge_dir,
        skip_download=args.skip_download,
    )
    print(f"Synchronized {len(copied)} ORCD Markdown documents.")
    print(f"Knowledge directory: {manifest['knowledge_dir']}")
    print(f"Source version: {manifest['source_commit']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
