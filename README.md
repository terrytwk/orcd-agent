# ORCD Agent

Lightweight local tools that help coding agents behave safely on MIT ORCD.

The project provides static agent rules, a runtime context command, local ORCD Markdown documentation, and Slurm starter templates. It deliberately avoids embeddings, hosted services, LLM calls, ranked retrieval, and automatic job submission.

## Install On ORCD

For the normal ORCD path, use the one-shot bootstrap:

```bash
curl -fsSL https://raw.githubusercontent.com/terrytwk/orcd-agent/main/scripts/bootstrap_orcd.sh | bash
```

The bootstrap prints each major step before running it. It installs ORCD Agent, exports `PATH` for the bootstrap process, adds a marked PATH block to your shell profile with a timestamped backup, loads Miniforge, and syncs local ORCD docs.

After it finishes, open a new shell so the profile update is picked up. The bootstrap exports `PATH` inside its own process, but a `curl ... | bash` script cannot modify the parent shell that launched it. To use `orcd-agent` immediately in that same terminal, run:

```bash
export PATH="$HOME/.orcd-agent/bin:$PATH"
```

For manual installation, non-ORCD environments, or debugging, see [Advanced / Manual Setup](#advanced--manual-setup).

## Quick Start

```bash
orcd-agent init
orcd-context
orcd-agent context --json
orcd-agent docs index
orcd-agent docs grep "miniforge"
orcd-agent docs read software/python.md
```

`orcd-agent init` copies ORCD guidance into `.orcd/AGENTS_ORCD.md`. Existing project `AGENTS.md` files are authoritative and are never overwritten.

If no `AGENTS.md` exists, init creates a small reference file that points agents to `.orcd/AGENTS_ORCD.md`. If `AGENTS.md` already exists, init leaves it untouched by default and tells you to load both files. To explicitly add only the small reference block, run:

```bash
orcd-agent init --append-reference
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

## Advanced / Manual Setup

Use these steps if you want to debug the install, run outside ORCD, test a fork, or avoid the one-shot bootstrap.

From a clone:

```bash
git clone https://github.com/terrytwk/orcd-agent.git
cd orcd-agent
./install.sh
export PATH="$HOME/.orcd-agent/bin:$PATH"
module load miniforge
python3 "$HOME/.orcd-agent/scripts/sync_docs.py"
```

From the hosted installer:

```bash
curl -fsSL https://raw.githubusercontent.com/terrytwk/orcd-agent/main/install.sh | bash
export PATH="$HOME/.orcd-agent/bin:$PATH"
module load miniforge
python3 "$HOME/.orcd-agent/scripts/sync_docs.py"
```

To persist `orcd-agent` for future shells when installing manually, add this line to your shell profile, usually `~/.bashrc` on ORCD:

```bash
export PATH="$HOME/.orcd-agent/bin:$PATH"
```

Set `ORCD_AGENT_REPO_URL` and `ORCD_AGENT_BRANCH` when testing a fork.

On ORCD, load Miniforge before syncing docs. Some system `python3` versions are too old for the sync script, while the Miniforge Python is current enough.

To run the bootstrap without updating your shell profile:

```bash
curl -fsSL https://raw.githubusercontent.com/terrytwk/orcd-agent/main/scripts/bootstrap_orcd.sh | ORCD_AGENT_UPDATE_PROFILE=0 bash
```

### Troubleshooting Shell Setup

You do not need this for a normal install. The bootstrap chooses a profile from your login shell automatically. If `orcd-agent` is still not found after opening a new shell, inspect your shell setup:

```bash
echo "host: $(hostname)"
echo "shell: ${SHELL:-unknown}"
echo "home: $HOME"
echo "pwd: $PWD"
echo "python3: $(command -v python3 || true)"
python3 --version 2>&1 || true
type module 2>/dev/null || true
module avail miniforge 2>&1 | head -40 || true
for f in "$HOME/.bashrc" "$HOME/.bash_profile" "$HOME/.profile" "$HOME/.zshrc"; do
  [ -e "$f" ] && echo "profile: $f"
done
```

### Documentation Sync

```bash
module load miniforge
python3 "$HOME/.orcd-agent/scripts/sync_docs.py"
```

By default, the sync script clones `https://github.com/mit-orcd/orcd-docs-edit.git`, identifies the canonical Markdown root, and atomically replaces `~/.orcd-agent/knowledge/` with a plain Markdown documentation tree. It also writes `~/.orcd-agent/knowledge/INDEX.md` and `~/.orcd-agent/knowledge/.manifest.json`.

Useful overrides:

```bash
module load miniforge
ORCD_DOCS_REPO=https://github.com/mit-orcd/orcd-docs-edit.git \
ORCD_DOCS_BRANCH=main \
python3 "$HOME/.orcd-agent/scripts/sync_docs.py"
```
