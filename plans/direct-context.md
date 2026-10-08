# Goal

Replace the existing ORCD documentation retrieval system completely.

Delete:

```text
BM25
chunking
ranked retrieval
top-k selection
tags/example-query retrieval logic
processed JSONL used only for search
embedding-ready retrieval code
```

The new architecture should be:

```text
ORCD docs
  ↓
sync canonical Markdown
  ↓
local structured docs tree
  ↓
coding agent navigates it directly
```

---

# 1. Target Structure

Store synchronized ORCD docs at:

```text
~/.orcd-agent/knowledge/
├── INDEX.md
├── running-jobs/
├── software/
├── storage/
├── accessing-orcd/
├── recipes/
└── .manifest.json
```

Preserve the upstream hierarchy and Markdown as closely as possible.

Do not chunk documents.

---

# 2. Remove Existing Retrieval Pipeline

Delete or refactor out:

```text
search.py
BM25 index code
chunk parser
ranking/scoring logic
top-k configuration
retrieval-specific JSONL generation
example-query expansion
retrieval tests
```

Remove commands such as:

```bash
orcd-agent search "..."
```

Do not retain backward compatibility.

Git history/branch is sufficient for recovering the old implementation.

---

# 3. Documentation Sync

Refactor `sync_docs.py`.

It should:

1. fetch/update the official ORCD docs source;
2. identify the canonical Markdown documentation root;
3. copy Markdown into `~/.orcd-agent/knowledge/`;
4. preserve relative directory/file structure;
5. preserve headings, code blocks, and links;
6. generate `INDEX.md`;
7. generate `.manifest.json`;
8. atomically replace the old local corpus after a successful sync.

Do not copy unnecessary build artifacts.

---

# 4. `INDEX.md`

Generate a lightweight high-level map.

Example:

```markdown
# MIT ORCD Documentation

## Running Jobs
Path: `running-jobs/`

Covers:
- Slurm
- batch jobs
- interactive jobs
- resource requests
- GPUs
- monitoring
- job arrays

## Software
Path: `software/`

Covers:
- modules
- Python
- Miniforge
- environments
- compiling software

## Storage
Path: `storage/`

Covers:
- home
- pool
- scratch
- temporary/high-I/O data

## Recipes
Path: `recipes/`

Covers common ORCD workflows and examples.
```

Keep it concise enough for an agent to read routinely.

---

# 5. Documentation CLI

Implement four simple commands.

## Index

```bash
orcd-agent docs index
```

Print `INDEX.md`.

## Tree

```bash
orcd-agent docs tree
```

Print a bounded tree of the documentation corpus.

Example:

```text
running-jobs/
  overview.md
  requesting-resources.md
  many-jobs.md

software/
  modules.md
  python.md
```

Only traverse the knowledge directory.

## Grep

```bash
orcd-agent docs grep "miniforge"
```

Search canonical Markdown files.

Prefer `rg` if available; otherwise use Python.

Return exact file/line matches.

No scoring or ranking.

## Read

```bash
orcd-agent docs read software/python.md
```

Return the source Markdown.

Optionally support:

```bash
orcd-agent docs read software/python.md --heading "Python environments"
```

if easy to implement cleanly.

---

# 6. Agent Instructions

Update `AGENTS.md` / `SKILL.md`.

Core guidance:

```markdown
## ORCD Documentation

Canonical local ORCD documentation is available through:

- `orcd-agent docs index`
- `orcd-agent docs tree`
- `orcd-agent docs grep "<term>"`
- `orcd-agent docs read <path>`

For ORCD-specific operational questions, consult the local canonical documentation rather than relying only on prior model knowledge.

Use the documentation like a small read-only codebase:
1. inspect the index/tree,
2. search likely terminology,
3. read relevant files,
4. follow related files when necessary.
```

Do not instruct the agent to formulate a retrieval query or request top-k chunks.

---

# 7. Direct Filesystem Access

The CLI must not be required for access.

The agent should also be able to use:

```bash
rg "miniforge" ~/.orcd-agent/knowledge
cat ~/.orcd-agent/knowledge/software/python.md
```

This is intentional.

The canonical representation is ordinary Markdown, not a proprietary index.

---

# 8. Safety Boundaries

All docs commands must be sandboxed to:

```text
~/.orcd-agent/knowledge/
```

Prevent:

```text
../ traversal
absolute external paths
symlink escape
recursive traversal outside knowledge/
```

For example:

```bash
orcd-agent docs read ../../.ssh/config
```

must fail.

`docs grep` must never expand its search scope outside the docs root.

---

# 9. Manifest

Generate:

```json
{
  "source": "mit-orcd/orcd-docs",
  "commit": "...",
  "synced_at": "...",
  "file_count": 87
}
```

Store as:

```text
~/.orcd-agent/knowledge/.manifest.json
```

Expose optionally:

```bash
orcd-agent docs status
```

Output:

```text
Source commit: ...
Last sync: ...
Files: ...
```

---

# 10. Existing HPC Context Integration

Do not change the existing generic runtime behavior.

`orcd-agent context` should continue providing:

```text
node type
Slurm allocation
GPU/CPU resources
loaded modules
project context when enabled
```

Documentation and runtime state remain separate:

```text
orcd-agent context
    = what environment am I currently in?

orcd-agent docs ...
    = what does ORCD say about this?
```

---

# 11. Project Runtime Integration

Do not add retrieval over project state.

If project runtime is enabled:

```text
.orcd/project.yaml
.orcd/runs/
```

the agent should use structured commands such as:

```bash
orcd-agent context --json
orcd-agent runs ...
```

The model combines:

```text
canonical ORCD docs
+
dynamic cluster context
+
project metadata
```

itself.

---

# 12. Remove Retrieval Dependencies

Review `pyproject.toml` / dependencies and remove packages used only for:

```text
BM25
ranking
tokenization for retrieval
vector/search indexing
```

The documentation layer should require little beyond the standard library.

Optional dependency:

```text
ripgrep
```

but provide a Python fallback.

---

# 13. Tests

## Sync

Test:

- docs copied correctly
- hierarchy preserved
- code blocks preserved
- deleted upstream files disappear after resync
- manifest generated
- sync failure does not destroy previous good corpus

## Tree

Test:

- nested files shown
- hidden/internal files filtered appropriately
- traversal bounded to knowledge root

## Grep

Test:

```bash
orcd-agent docs grep "miniforge"
```

finds expected files.

Test multiple-word and regex-safe behavior.

## Read

Test:

- valid Markdown path
- missing file
- traversal attack
- symlink escape

## Agent instructions

Verify no remaining references to:

```text
BM25
top-k
orcd-agent search
retrieval chunks
```

---

# 14. Cleanup

Search the repo for legacy concepts:

```text
search
retrieval
BM25
chunk
top_k
example_queries
rank
score
```

Remove code that only supported the old retrieval architecture.

Be careful not to delete unrelated uses of terms like `search` or `score`.

---

# 15. Acceptance Criteria

After installation:

```bash
orcd-agent docs index
```

shows a compact map.

```bash
orcd-agent docs tree
```

shows the canonical hierarchy.

```bash
orcd-agent docs grep "cpus-per-task"
```

locates the relevant ORCD documentation.

```bash
orcd-agent docs read running-jobs/requesting-resources.md
```

returns the source directly.

A coding agent should be able to solve ORCD-specific questions by recursively navigating these files without any ranked retrieval layer.

---

# Final Architecture

```text
Official ORCD docs
      ↓
sync_docs.py
      ↓
canonical Markdown tree
      ↓
┌────────┬────────┬────────┐
│ index  │ tree   │ grep   │ read
└────────┴────────┴────────┘
               ↓
          coding agent
          /          \
         ↓            ↓
context --json   project runtime
         \            /
          \          /
           agent action
```

The documentation layer should now be **filesystem-native, deterministic, and model-directed**.