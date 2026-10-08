# ORCD Agent Prototype — Implementation Plan

## Goal

Build a lightweight tool that makes coding agents behave safely and correctly on MIT ORCD.

The MVP should provide:

1. **Static ORCD agent rules**
2. **Dynamic runtime context**
3. **Local access to ORCD documentation**
4. **Simple one-command installation**

Do not build a full RAG system or agent-specific `SKILL.md` yet.

---

## Repository structure

```text
orcd-agent/
├── README.md
├── install.sh
├── AGENTS.md
├── bin/
│   ├── orcd-agent
│   ├── orcd-context
│   └── orcd-search
├── scripts/
│   └── sync_docs.py
├── docs/
│   ├── raw/
│   ├── processed/
│   └── manifest.json
└── templates/
    ├── cpu.sbatch
    └── gpu.sbatch
```

---

## 1. `AGENTS.md`

Create a concise agent instruction file containing critical ORCD rules.

Include at minimum:

- Never run expensive computation on login nodes.
- Never run unbounded filesystem searches such as:
  - `find /`
  - `grep -R /`
  - `du /`
- Restrict file searches to the current project unless explicitly necessary.
- Check modules before installing software.
- For Python, check/load Miniforge first:
  ```bash
  module avail miniforge
  module load miniforge
  ```
- Use Slurm for computational workloads.
- Put environment/module setup inside Slurm scripts.
- Run `orcd-context` at the beginning of a session.
- Use `orcd-search "<question>"` for ORCD-specific questions.

Keep this file small: ideally <4,000 tokens.

---

## 2. `orcd-context`

Implement as Bash or Python.

Purpose: tell the agent what environment it is currently running in.

Output:

```text
ORCD Agent Context
------------------
Host: ...
Node type: LOGIN / COMPUTE / UNKNOWN
Slurm job: ...
Partition: ...
CPUs: ...
GPUs: ...
Memory: ...
Current directory: ...
Loaded modules: ...

Recommended behavior:
  ✓ ...
  ✗ ...
```

Detect using environment variables and commands such as:

```bash
hostname
pwd
env | grep '^SLURM_'
module list
```

Important:

- Do not run expensive cluster-wide commands.
- If no Slurm allocation is detected, default conservatively.
- Clearly warn when likely running on a login node.

---

## 3. ORCD documentation synchronization

Implement:

```bash
python scripts/sync_docs.py
```

Prefer pulling the source Markdown from the public ORCD documentation GitHub repository rather than scraping rendered HTML.

The script should:

1. Download/update ORCD docs.
2. Preserve source file hierarchy.
3. Parse Markdown into sections based on headings.
4. Preserve:
   - title
   - heading hierarchy
   - source path
   - source URL
   - body text
   - code blocks
5. Produce a searchable JSONL file.

Example:

```json
{
  "title": "Python",
  "section": "Installing Python Packages",
  "source_path": "software/python.md",
  "url": "https://orcd-docs.mit.edu/software/python/",
  "text": "...",
  "code_blocks": [
    "module load miniforge"
  ]
}
```

Output:

```text
docs/processed/orcd_docs.jsonl
```

Also generate:

```text
docs/manifest.json
```

containing source commit/version and sync timestamp.

---

## 4. `orcd-search`

Build a simple local documentation search CLI.

Usage:

```bash
orcd-search "how do I request a GPU?"
```

For MVP, use keyword/BM25-style search. Do not add embeddings unless necessary.

Search:

```text
docs/processed/orcd_docs.jsonl
```

Return the top 3–5 sections:

```text
[1] Running Jobs > GPU Jobs

Relevant text...

Commands:
  #SBATCH --gres=gpu:1

Source:
https://orcd-docs.mit.edu/...
```

Prioritize:

- heading matches
- exact keywords
- code blocks
- short useful sections

Keep output concise enough to feed directly into an LLM context window.

---

## 5. Slurm templates

Create minimal templates:

```text
templates/cpu.sbatch
templates/gpu.sbatch
```

They should demonstrate:

```bash
#!/bin/bash
#SBATCH ...

module load miniforge

python script.py
```

Do not hardcode overly specific resource requests.

Add comments telling the agent/user to adjust partition, CPUs, memory, GPU count, and runtime.

---

## 6. Installation

Create:

```bash
install.sh
```

Install under:

```text
~/.orcd-agent/
```

Example:

```text
~/.orcd-agent/
├── bin/
├── docs/
├── templates/
└── AGENTS.md
```

Add or instruct the user to add:

```bash
export PATH="$HOME/.orcd-agent/bin:$PATH"
```

Support:

```bash
curl -fsSL <raw-install-url> | bash
```

Also allow normal GitHub clone for contributors.

---

## 7. Project initialization

Optional but useful command:

```bash
orcd-agent init
```

It should copy or symlink:

```text
.orcd/AGENTS_ORCD.md
```

into the current project.

Existing project `AGENTS.md` is authoritative for project-specific instructions. ORCD adds complementary HPC guidance without replacing or rewriting it.

`orcd-agent init` must never overwrite an existing `AGENTS.md`.

Best behavior:

- Keep ORCD's generic instructions in a separate project file, `.orcd/AGENTS_ORCD.md`, sourced from the installed `~/.orcd-agent/AGENTS.md`.
- During project init, detect whether `AGENTS.md` already exists.
- If `AGENTS.md` exists, leave it untouched by default and tell the user/agent tooling to load both `AGENTS.md` and `.orcd/AGENTS_ORCD.md`.
- Optionally support an explicit approval flag, such as `--append-reference`, that appends only a small reference block to the existing `AGENTS.md`.
- If no `AGENTS.md` exists, create a small reference-only `AGENTS.md` that points to `.orcd/AGENTS_ORCD.md`; do not copy the full ORCD instructions into project `AGENTS.md`.

Optional reference block:

```markdown
## ORCD / HPC context

For ORCD-specific environment and execution guidance, also read:

`.orcd/AGENTS_ORCD.md`

Before expensive work, run:

`orcd-agent context --json`
```

Also support:

```bash
orcd-agent context --json
```

as a wrapper around machine-readable runtime context.

---

## 8. Testing

Add basic tests for:

### `orcd-context`
- no Slurm environment
- simulated Slurm allocation
- missing `module` command
- output never triggers expensive filesystem operations

### `sync_docs.py`
- parses headings correctly
- preserves code blocks
- generates valid JSONL
- handles changed/new documentation

### `orcd-search`
- `"miniforge"` finds Python/module documentation
- `"GPU"` finds Slurm/GPU documentation
- `"storage"` finds storage documentation
- returns source URLs

### `orcd-agent init`
- creates `.orcd/AGENTS_ORCD.md`
- never overwrites an existing `AGENTS.md`
- leaves existing `AGENTS.md` untouched by default
- appends only the small ORCD reference block when the user explicitly passes `--append-reference`
- creates only a reference `AGENTS.md` when no project `AGENTS.md` exists

---

## MVP acceptance criteria

The project is successful if a user can run:

```bash
curl -fsSL <installer> | bash

cd my-project
orcd-agent init

orcd-context

orcd-search "how should I set up Python?"
```

and a coding agent reading `AGENTS.md` will:

- avoid expensive login-node work,
- avoid filesystem-wide searches,
- check modules before creating environments,
- use Slurm for compute,
- retrieve ORCD-specific guidance when needed.

If a project already has `AGENTS.md`, that file remains untouched and authoritative. ORCD guidance is installed as `.orcd/AGENTS_ORCD.md`, and the user/agent can either load both files or explicitly append the small ORCD reference block.

## Non-goals for v0.1

Do not implement yet:

- vector databases
- embeddings
- hosted backend
- LLM API calls
- full RAG
- VS Code extension
- Codex-specific skill
- Claude-specific skill
- automatic Slurm job submission

First make the local, agent-agnostic layer reliable.
