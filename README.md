# ORCD Agent

Lightweight local tools that help coding agents behave safely on MIT ORCD.

The project provides static agent rules, a runtime context command, local ORCD documentation search, and Slurm starter templates. It deliberately avoids embeddings, hosted services, LLM calls, and automatic job submission.

## Install

From a clone:

```bash
./install.sh
export PATH="$HOME/.orcd-agent/bin:$PATH"
```

From a hosted installer:

```bash
curl -fsSL <raw-install-url> | bash
export PATH="$HOME/.orcd-agent/bin:$PATH"
```

Set `ORCD_AGENT_REPO_URL` and `ORCD_AGENT_BRANCH` when testing a fork.

## Quick Start

```bash
orcd-agent init
orcd-context
orcd-agent context --json
python scripts/sync_docs.py
orcd-search "how should I set up Python?"
```

`orcd-agent init` copies ORCD guidance into `.orcd/AGENTS_ORCD.md`. Existing project `AGENTS.md` files are authoritative and are never overwritten.

If no `AGENTS.md` exists, init creates a small reference file that points agents to `.orcd/AGENTS_ORCD.md`. If `AGENTS.md` already exists, init leaves it untouched by default and tells you to load both files. To explicitly add only the small reference block, run:

```bash
orcd-agent init --append-reference
```

## Documentation Sync

```bash
python scripts/sync_docs.py
```

By default, the sync script clones `https://github.com/mit-orcd/orcd-docs-edit.git`, preserves the source Markdown hierarchy under `docs/raw/orcd-docs`, parses headings and code blocks, writes `docs/processed/orcd_docs.jsonl`, and records sync metadata in `docs/manifest.json`.

Useful overrides:

```bash
ORCD_DOCS_REPO=https://github.com/mit-orcd/orcd-docs-edit.git \
ORCD_DOCS_BRANCH=main \
python scripts/sync_docs.py
```

## Slurm Templates

Starter scripts live in `templates/cpu.sbatch` and `templates/gpu.sbatch`. Adjust partition, runtime, CPUs, memory, and GPU count before submitting.
