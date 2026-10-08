# ORCD Agent

Lightweight local tools that help coding agents behave safely on MIT ORCD.

The project provides static agent rules, a runtime context command, local ORCD Markdown documentation, and Slurm starter templates. It deliberately avoids embeddings, hosted services, LLM calls, ranked retrieval, and automatic job submission.

## Install

From a clone:

```bash
git clone https://github.com/terrytwk/orcd-agent.git
cd orcd-agent
./install.sh
export PATH="$HOME/.orcd-agent/bin:$PATH"
python3 "$HOME/.orcd-agent/scripts/sync_docs.py"
```

From a hosted installer:

```bash
curl -fsSL https://raw.githubusercontent.com/terrytwk/orcd-agent/main/install.sh | bash
export PATH="$HOME/.orcd-agent/bin:$PATH"
python3 "$HOME/.orcd-agent/scripts/sync_docs.py"
```

Set `ORCD_AGENT_REPO_URL` and `ORCD_AGENT_BRANCH` when testing a fork.

## Quick Start

```bash
orcd-agent init
orcd-context
orcd-agent context --json
python3 "$HOME/.orcd-agent/scripts/sync_docs.py"
orcd-agent docs index
orcd-agent docs grep "miniforge"
orcd-agent docs read software/python.md
```

`orcd-agent init` copies ORCD guidance into `.orcd/AGENTS_ORCD.md`. Existing project `AGENTS.md` files are authoritative and are never overwritten.

If no `AGENTS.md` exists, init creates a small reference file that points agents to `.orcd/AGENTS_ORCD.md`. If `AGENTS.md` already exists, init leaves it untouched by default and tells you to load both files. To explicitly add only the small reference block, run:

```bash
orcd-agent init --append-reference
```

## Documentation Sync

```bash
python3 "$HOME/.orcd-agent/scripts/sync_docs.py"
```

By default, the sync script clones `https://github.com/mit-orcd/orcd-docs-edit.git`, identifies the canonical Markdown root, and atomically replaces `~/.orcd-agent/knowledge/` with a plain Markdown documentation tree. It also writes `~/.orcd-agent/knowledge/INDEX.md` and `~/.orcd-agent/knowledge/.manifest.json`.

Useful overrides:

```bash
ORCD_DOCS_REPO=https://github.com/mit-orcd/orcd-docs-edit.git \
ORCD_DOCS_BRANCH=main \
python3 "$HOME/.orcd-agent/scripts/sync_docs.py"
```

## Documentation Access

The synchronized docs are ordinary Markdown. Agents can use either the CLI:

```bash
orcd-agent docs index
orcd-agent docs tree
orcd-agent docs grep "GPU"
orcd-agent docs read running-jobs/requesting-resources.md
orcd-agent docs status
```

or direct filesystem tools:

```bash
rg "miniforge" ~/.orcd-agent/knowledge
cat ~/.orcd-agent/knowledge/software/python.md
```

## Design Rationale

ORCD Agent treats documentation as a small local knowledge base that agents can inspect directly, rather than as a hidden retrieval index. The ORCD docs are compact enough that a coding agent can build its own context by reading the map, grepping for terms, and opening the relevant Markdown files.

This follows a broader shift away from heavily hand-designed retrieval layers for small, well-structured corpora. Instead of pre-chunking, ranking, and guessing top-k snippets, the tool exposes canonical source files and lets the agent navigate them like a read-only codebase. That keeps behavior deterministic, debuggable, and easy to verify with normal shell tools.

The older BM25-style retrieval prototype is intentionally not kept in this main implementation. If you want that simpler ranked-search version for comparison or experiments, use the `bm25-retrieval` branch.

## Slurm Templates

Starter scripts live in `templates/cpu.sbatch` and `templates/gpu.sbatch`. Adjust partition, runtime, CPUs, memory, and GPU count before submitting.
