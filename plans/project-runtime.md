# Agent-First Project Runtime for ORCD

## Goal

Build a lightweight project-aware runtime for coding agents working on ORCD.

The runtime should provide persistent operational memory about:

- project storage conventions
- environments/modules
- execution specs
- Slurm resources
- run provenance
- previous resource usage
- expected runtime from comparable runs
- links to scientific experiment tracking systems such as W&B

The runtime should **not become a full experiment-management framework**.

Its role is:

> Connect coding agents, project infrastructure, Slurm execution, and historical operational context.

---

# 1. Existing Assumptions

The generic ORCD/HPC-awareness layer already exists and provides:

```text
AGENTS.md / SKILL.md
orcd-agent context
ORCD documentation navigation
login vs compute-node awareness
Slurm/module guardrails
```

Project runtime is optional and only activates when:

```text
.orcd/project.yaml
```

exists.

Running:

```bash
orcd-agent project init
```

creates this project-specific state.

Without it, generic ORCD behavior remains unchanged.

---

# 2. Core Design Boundary

Keep four concepts separate:

```text
ORCD docs / HPC layer
    = cluster knowledge

project.yaml
    = stable project infrastructure

execution spec
    = command + resources + references to scientific configuration

run record
    = immutable record of what actually happened

W&B / MLflow / Hydra
    = scientific experiment management
```

Do not duplicate scientific configuration unnecessarily.

---

# 3. Project Layout

```text
.orcd/
├── project.yaml
├── executions/
├── runs/
├── generated/
└── state/
```

Avoid storing scientific experiment definitions here unless they are specifically execution-related.

Existing configs may live elsewhere:

```text
configs/
hydra/
experiments/
wandb/
```

The ORCD runtime should reference them.

---

# 4. Project Configuration

`.orcd/project.yaml` should contain relatively stable operational knowledge.

Example:

```yaml
version: 1

project:
  name: flavorbert

storage:
  datasets_root: /orcd/pool/.../datasets
  working_data_root: /orcd/scratch/.../datasets
  checkpoints: /orcd/pool/.../checkpoints
  outputs: /orcd/pool/.../outputs
  temp: /orcd/scratch/.../tmp

environment:
  modules:
    - miniforge

  conda_env: flavorbert

execution:
  default_workdir: .
  default_entrypoint: src/train.py

resource_profiles:
  h200:
    gpu_type: H200
    gpus: 1
    cpus: 8
    memory: 64G

  l40:
    gpu_type: L40
    gpus: 1
    cpus: 8
    memory: 64G

tracking:
  provider: wandb
  entity: optional
  project: flavorbert
```

Do not store individual learning rates, augmentations, seeds, etc. here.

---

# 5. Project Discovery

Search upward from the current directory for:

```text
.orcd/project.yaml
```

Expose internally:

```python
find_project_root()
load_project_config()
```

If no project config exists:

```text
orcd-agent context
```

must behave exactly as the generic HPC-aware implementation does today.

---

# 6. Dataset and Storage Metadata

Treat datasets as optional project metadata, not a full dataset-management system.

Example:

```yaml
datasets:
  gems:
    canonical_path: /orcd/pool/.../gems
    working_path: /orcd/scratch/.../gems
    format: parquet

  foodb:
    canonical_path: /orcd/pool/.../foodb
    working_path: /orcd/scratch/.../foodb
```

Support optional labels:

```yaml
metadata:
  role: training
  version: "2026-09"
```

Do not implement dataset version-control infrastructure.

Do not require all datasets to be registered.

---

# 7. Execution Specification

An execution spec should describe operational execution, not the entire scientific experiment.

Example:

```yaml
name: flavorbert_train

command:
  - python
  - src/train.py
  - --config
  - configs/foodb_10x.yaml

workdir: .

environment:
  modules:
    - miniforge
  conda_env: flavorbert

resources:
  profile: h200
  time: 04:00:00

inputs:
  - dataset:gems

outputs:
  checkpoints: /orcd/pool/.../checkpoints
```

Scientific configuration remains external:

```text
configs/foodb_10x.yaml
```

or Hydra/W&B/etc.

---

# 8. Resolved Execution Object

Before every run, generate a single resolved execution object.

Example:

```yaml
command:
  - python
  - src/train.py
  - --config
  - configs/foodb_10x.yaml

workdir: /project/root

environment:
  modules:
    - miniforge
  conda_env: flavorbert

resources:
  gpu_type: H200
  gpus: 1
  cpus: 8
  memory: 64G
  time: 04:00:00

references:
  scientific_config:
    path: configs/foodb_10x.yaml
    sha256: ...
```

Store this exact resolved object with every run.

This is the reproducibility anchor.

---

# 9. Scientific Config References

Do not duplicate an entire Hydra/config system.

Instead capture:

```yaml
scientific_config:
  path: configs/foodb_10x.yaml
  sha256: ...
```

Optionally, if cheap and deterministic, also store a resolved snapshot:

```text
resolved_scientific_config.yaml
```

But this should be derived from the existing config system, not reimplemented.

---

# 10. Agent-Facing Context

Extend:

```bash
orcd-agent context --json
```

to include project information when enabled.

Example:

```json
{
  "cluster": {
    "node_type": "compute",
    "gpu_type": "H200",
    "gpus": 1
  },
  "project": {
    "name": "flavorbert",
    "root": "...",
    "environment": {
      "modules": ["miniforge"],
      "conda_env": "flavorbert"
    }
  },
  "storage": {
    "datasets_root": "...",
    "checkpoints": "..."
  },
  "recent_runs": [
    {
      "run_id": "...",
      "gpu_type": "H200",
      "runtime_seconds": 10320
    }
  ],
  "tracking": {
    "provider": "wandb",
    "project": "flavorbert"
  }
}
```

JSON should be the primary agent interface.

Human-readable output remains available.

---

# 11. Run Records

Each execution creates:

```text
.orcd/runs/<run-id>/
├── run.yaml
├── resolved-execution.yaml
├── stdout.log
└── stderr.log
```

Example:

```yaml
run:
  id: ...
  status: completed
  kind: validation

code:
  git_commit: ...
  git_dirty: false

execution:
  command: ...
  config_ref: configs/foodb_10x.yaml
  config_hash: ...

resources_requested:
  gpu_type: H200
  gpus: 1
  cpus: 8
  memory: 64G
  time: 04:00:00

resources_actual:
  wall_time_seconds: ...
  max_memory: ...

slurm:
  job_id: ...
  partition: ...

tracking:
  provider: wandb
  run_id: optional
```

Do not capture every ML metric locally.

---

# 12. Run Kinds

Explicitly distinguish run intent.

Support:

```text
debug
validation
benchmark
full
sweep
```

Example:

```yaml
run:
  kind: validation
```

This matters because:

```text
20-minute validation run
```

should not automatically imply:

```text
full training runtime ≈ 20 minutes
```

Historical resource estimation should prefer comparable run kinds.

---

# 13. Interactive Execution

Support:

```bash
orcd-agent run interactive execution.yaml
```

Use for:

- debugging
- validating paths/configs
- smoke tests
- memory checks
- confirming environment setup

Interactive execution and batch execution must use the same resolved execution object.

If no allocation exists, recommend or optionally create one.

Do not silently allocate resources by default.

---

# 14. Batch Execution

Support:

```bash
orcd-agent run submit execution.yaml
```

Generate:

```text
.orcd/generated/<run-id>.sbatch
```

from the same resolved execution object.

Support:

```bash
orcd-agent run submit execution.yaml --dry-run --json
```

Return:

```json
{
  "command": "...",
  "sbatch_path": "...",
  "resources": {...}
}
```

---

# 15. Interactive → Batch Promotion

Support:

```bash
orcd-agent promote <run-id> --json
```

Promotion should:

1. require a successful source run;
2. preserve command and scientific config reference;
3. preserve dataset/input references;
4. modify only operational resource fields;
5. show a structured diff;
6. never submit automatically by default.

Example:

```json
{
  "source_run": "...",
  "resource_changes": {
    "memory": {
      "old": "64G",
      "new": "40G"
    }
  },
  "scientific_config_changed": false
}
```

Only promote resource estimates when source run kind is appropriate.

A `debug` run should generally not be used to estimate full-run runtime.

---

# 16. Completed Run Analysis

Support:

```bash
orcd-agent run analyze <run-id>
```

Collect available Slurm/accounting/jobstats information.

Store:

```yaml
resources_actual:
  wall_time_seconds: ...
  max_rss: ...
  state: COMPLETED
  exit_code: ...
```

Capture GPU statistics when available, but do not make them required.

---

# 17. Run Store Abstraction

Do not tightly couple queries to directory scanning.

Implement:

```python
class RunStore:
    list_runs(...)
    get_run(...)
    save_run(...)
    find_similar(...)
```

Initial backend:

```text
filesystem YAML
```

Future backend:

```text
SQLite
```

This prevents `.orcd/runs/` from becoming an architectural dead end.

---

# 18. Similar Run Matching

Start with deterministic matching.

Use fields such as:

```text
same entrypoint
same scientific config hash
same dataset/input references
same GPU type
same run kind
same user labels
```

Allow optional structured labels:

```yaml
labels:
  model: flavorbert-base
  dataset_variant: foodb_10x
  batch_size: 256
  precision: bf16
```

These are optional metadata for matching, not a required experiment schema.

---

# 19. Resource Estimation

Support:

```bash
orcd-agent estimate execution.yaml --json
```

Use comparable completed runs.

Return:

```json
{
  "status": "ok",
  "comparable_runs": 4,
  "runtime": {
    "median_seconds": 10260,
    "min_seconds": 9780,
    "max_seconds": 11100
  },
  "recommended": {
    "time": "03:30:00",
    "memory": "40G"
  },
  "confidence": "moderate",
  "evidence": [
    "run-id-1",
    "run-id-2"
  ]
}
```

Rules:

- use medians
- report range
- report sample count
- show which runs were used
- avoid cross-GPU extrapolation initially
- avoid using debug runs for full-run prediction
- return `insufficient_history` when appropriate

Do not pretend to have a learned performance model.

---

# 20. Optional W&B Integration

Implement W&B as an optional adapter.

The runtime should work fully without W&B.

Project config:

```yaml
tracking:
  provider: wandb
  entity: optional
  project: flavorbert
```

Do not store API keys in project files.

Use the standard W&B authentication mechanism.

---

# 21. W&B Adapter

Define an interface:

```python
class TrackingProvider:
    list_runs(...)
    get_run(...)
    compare_runs(...)
```

Implement:

```python
class WandBProvider(TrackingProvider):
    ...
```

Initial integration should be read-oriented.

Support:

```bash
orcd-agent tracking runs --json

orcd-agent tracking show <wandb-run-id> --json

orcd-agent tracking compare <run1> <run2> --json
```

---

# 22. W&B Responsibilities

Use W&B for:

```text
experiment configs
training/validation metrics
loss curves
evaluation metrics
artifacts
scientific run comparisons
```

Use ORCD runtime for:

```text
Slurm job
node
GPU type
CPU
memory
wall time
storage paths
execution command
environment
run provenance
```

Do not duplicate all W&B metadata locally.

---

# 23. Cross-Link ORCD Runs and W&B Runs

Local run record:

```yaml
tracking:
  provider: wandb
  entity: ...
  project: flavorbert
  run_id: abc123
```

This allows the coding agent to combine:

```text
ORCD:
  H200
  3h02m
  34 GB RAM

W&B:
  batch size 256
  learning rate 1e-4
  val F1 0.83
```

without copying the entire W&B run into `.orcd/`.

---

# 24. Agent Queries Across Both Sources

The agent should be able to answer questions like:

```text
Which H200 run had the best validation F1?

How long did the best-performing configuration take?

Which batch sizes OOMed?

What configuration produced this checkpoint?

Did L40 and H200 runs use the same scientific config?
```

The coding agent combines:

```text
local ORCD run data
+
W&B API data
```

Do not build a complex query engine initially.

Expose clean structured data and let the model reason over it.

---

# 25. W&B Failure Behavior

If W&B is unavailable:

```text
network unavailable
credentials missing
project not configured
run missing
```

return structured errors.

Example:

```json
{
  "status": "unavailable",
  "reason": "wandb_not_authenticated"
}
```

Local ORCD runtime must continue working normally.

---

# 26. Agent Mutation Policy

The coding agent may automatically read:

```text
project.yaml
context --json
run history
W&B runs
storage metadata
```

Be more conservative about persistent mutation.

Do not silently:

- rewrite project configuration
- create new canonical dataset paths
- modify scientific configs
- submit expensive jobs
- delete W&B resources
- overwrite run records

Persistent changes should be explicit and inspectable.

---

# 27. Agent Instructions

Add:

```markdown
When `.orcd/project.yaml` exists:

1. Run `orcd-agent context --json` before assuming project paths,
   environment, or resource conventions.

2. Reuse existing project storage/layout conventions.

3. Treat scientific configs as external sources of truth.
   Do not duplicate or rewrite them into ORCD metadata unnecessarily.

4. Query previous runs before estimating runtime/resources.

5. Use W&B, when configured, for scientific metrics and experiment configs.

6. Use local ORCD run records for HPC execution/resource history.

7. Prefer interactive validation for uncertain workloads.

8. Promote validated execution to batch while preserving scientific configuration.
```

---

# 28. Machine-Readable First

Every important command should support:

```text
--json
```

At minimum:

```bash
orcd-agent context --json

orcd-agent project describe --json

orcd-agent run list --json

orcd-agent run show <run-id> --json

orcd-agent run analyze <run-id> --json

orcd-agent runs similar ... --json

orcd-agent estimate ... --json

orcd-agent promote ... --json

orcd-agent tracking runs --json

orcd-agent tracking show ... --json
```

JSON interfaces should have stable schemas.

---

# 29. Implementation Order

## Phase 1 — Simplified project model

Implement:

```text
project discovery
project.yaml
typed schemas
context --json
storage/dataset metadata
```

## Phase 2 — Execution provenance

Implement:

```text
execution spec
resolved execution object
run IDs
run.yaml
git metadata
scientific config references/hashes
```

## Phase 3 — Execution backends

Implement:

```text
interactive backend
Slurm batch backend
dry-run
shared resolved execution object
```

## Phase 4 — History

Implement:

```text
RunStore abstraction
run list/show
Slurm accounting ingestion
similar-run matching
resource estimate
```

## Phase 5 — Promotion

Implement:

```text
run-kind-aware promotion
resource recommendation
structured diff
```

## Phase 6 — Optional W&B read adapter

Implement:

```text
TrackingProvider interface
WandBProvider
tracking runs
tracking show
tracking compare
ORCD ↔ W&B run linking
```

---

# 30. Explicit Non-Goals

Do not build:

```text
custom experiment tracker
custom metric dashboard
full Hydra replacement
dataset version-control system
learned runtime predictor
cross-project global database
automatic scientific hyperparameter inference
W&B write/delete management
complex query language
```

---

# 31. Acceptance Scenario

Existing project:

```text
FlavorBERT
scientific config: configs/foodb_10x.yaml
W&B tracking enabled
```

Agent begins with:

```bash
orcd-agent context --json
```

It learns:

```text
project paths
environment
current allocation
tracking provider
recent operational runs
```

It can inspect previous ORCD runs:

```bash
orcd-agent run list --json
```

and scientific runs:

```bash
orcd-agent tracking runs --json
```

Suppose the user asks:

> Try a new augmentation configuration and compare it to the previous best run.

The agent:

1. inspects W&B for the best scientific run;
2. finds its linked ORCD run;
3. learns the runtime/resources used;
4. creates or references the new scientific config;
5. creates an execution spec pointing to that config;
6. validates interactively;
7. records operational provenance;
8. promotes to batch if appropriate.

The agent does not need the user to re-explain:

```text
where the data lives
which environment to use
what resources similar runs used
which W&B project contains previous experiments
```

---

# Core Objective

The runtime should function as:

> **Persistent operational memory and execution infrastructure for coding agents on HPC.**

It should complement scientific tooling rather than replace it.

The clean boundary is:

```text
Hydra / configs / W&B
        ↓
scientific experiment

ORCD project runtime
        ↓
how and where that experiment executes

coding agent
        ↓
reason across both
```