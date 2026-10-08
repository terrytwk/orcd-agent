# Agent-First Project Runtime for ORCD

## Goal

Build a project-aware runtime layer for coding agents working on ML projects in ORCD.

Assume the generic ORCD/HPC awareness layer already exists and handles:

- login vs compute node awareness
- Slurm rules
- module system
- safe filesystem behavior
- ORCD documentation access
- `orcd-agent context`

This new layer should give coding agents persistent project-specific knowledge about:

- datasets and dataset variants
- train/validation/test splits
- augmentation strategies
- model configurations
- hyperparameters
- storage conventions
- previous runs
- resource usage
- expected runtimes
- successful execution patterns
- interactive → batch promotion

The primary consumer is the coding agent, not the human user.

Project runtime must be completely opt-in. orcd-agent must never create .orcd/, track runs, infer project metadata, or enable project-specific behavior unless the user or agent explicitly runs orcd-agent project init or a valid .orcd/project.yaml already exists.

And for context:
No .orcd/project.yaml
→ cluster/HPC context only

.orcd/project.yaml exists
→ cluster/HPC context + project context

---

# 1. Design Principle

Separate information into four layers:

```text
cluster context
    ↓
project infrastructure
    ↓
experiment configuration
    ↓
run history
```

Specifically:

```text
ORCD layer
    = cluster knowledge

.orcd/project.yaml
    = stable project knowledge

experiment spec
    = dataset/model/hyperparameter choices

run record
    = what actually happened
```

Do not mix these unnecessarily.

---

# 2. Project Layout

Each project may contain:

```text
.orcd/
├── project.yaml
├── experiments/
├── runs/
├── generated/
└── state/
```

Example:

```text
.orcd/
├── project.yaml
├── experiments/
│   ├── foodb_10x.yaml
│   └── pubchem_baseline.yaml
├── runs/
│   └── <run-id>/
└── generated/
```

---

# 3. Project Discovery

Search upward from the current directory for:

```text
.orcd/project.yaml
```

Expose:

```python
find_project_root()
load_project_config()
```

The existing:

```bash
orcd-agent context
```

should automatically include project information when available.

If no project config exists, generic HPC-aware behavior must remain unchanged.

---

# 4. Stable Project Configuration

Use `.orcd/project.yaml` only for relatively stable project knowledge.

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
```

Do not store individual learning rates, seeds, splits, or augmentation levels here.

---

# 5. Dataset Registry

Datasets should be first-class entities.

Example:

```yaml
datasets:
  foodb:
    canonical_path: /orcd/pool/.../foodb
    working_path: /orcd/scratch/.../foodb

  pubchem:
    canonical_path: /orcd/pool/.../pubchem
    working_path: /orcd/scratch/.../pubchem
```

Support variants separately.

Example:

```yaml
dataset_variants:
  foodb_base:
    dataset: foodb
    split: split_v1
    augmentation: none

  foodb_5x:
    dataset: foodb
    split: split_v1
    augmentation:
      type: random_smiles
      multiplier: 5

  foodb_10x:
    dataset: foodb
    split: split_v2
    augmentation:
      type: random_smiles
      multiplier: 10
```

Dataset variants should be referenced by name from experiments.

---

# 6. Experiment Specification

Experiments should describe scientific choices.

Example:

```yaml
name: flavorbert_foodb_10x

dataset:
  variant: foodb_10x

model:
  name: flavorbert-base
  config: configs/model/base.yaml

training:
  batch_size: 256
  learning_rate: 1e-4
  epochs: 10
  precision: bf16
  seed: 42

objectives:
  mlm: true
  occurrence: true
  contrastive: false

resources:
  profile: h200
  time: 04:00:00
```

Support arbitrary user-defined metadata:

```yaml
metadata:
  augmentation_family: smiles
  ablation_group: occurrence_loss
```

Do not impose a rigid ML schema beyond common fields.

---

# 7. Config Composition

Resolve configuration in this order:

```text
project defaults
      ↓
dataset variant
      ↓
resource profile
      ↓
experiment spec
      ↓
CLI / agent override
```

Produce one fully resolved object.

Example:

```yaml
resolved:
  dataset:
    name: foodb
    split: split_v2
    augmentation:
      type: random_smiles
      multiplier: 10

  training:
    batch_size: 256
    learning_rate: 1e-4
    seed: 42

  resources:
    gpu_type: H200
    gpus: 1
    memory: 64G

  paths:
    dataset: /orcd/scratch/.../foodb
    checkpoint: /orcd/pool/.../checkpoints/...
```

Save this with every run.

---

# 8. Agent-Facing Context

Extend:

```bash
orcd-agent context --json
```

Return structured information optimized for agents.

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
  "datasets": {
    "foodb": {
      "canonical": "...",
      "working": "..."
    }
  },
  "recent_runs": [
    {
      "experiment": "foodb_10x",
      "gpu": "H200",
      "runtime_seconds": 10320
    }
  ]
}
```

The agent should query this before making assumptions.

Human-readable output should remain available, but JSON is the primary interface.

---

# 9. Agent Query API

Add structured commands intended for coding agents:

```bash
orcd-agent project describe --json

orcd-agent datasets list --json

orcd-agent datasets show foodb_10x --json

orcd-agent runs list --json

orcd-agent runs similar \
  --experiment foodb_10x.yaml \
  --json

orcd-agent estimate \
  --experiment foodb_10x.yaml \
  --json
```

Prefer stable JSON schemas.

---

# 10. Run Records

Each run should create:

```text
.orcd/runs/<run-id>/
├── run.yaml
├── resolved.yaml
├── stdout.log
└── stderr.log
```

Record:

```yaml
run:
  id: ...
  status: completed

code:
  git_commit: ...
  git_dirty: false

experiment:
  name: flavorbert_foodb_10x

dataset:
  dataset: foodb
  split: split_v2
  augmentation:
    type: random_smiles
    multiplier: 10

training:
  batch_size: 256
  learning_rate: 1e-4
  seed: 42

resources_requested:
  gpu_type: H200
  gpus: 1
  memory: 64G
  time: 04:00:00

resources_actual:
  runtime_seconds: ...
  max_memory: ...

slurm:
  job_id: ...
```

Preserve arbitrary experiment metadata.

---

# 11. Interactive Execution

Support:

```bash
orcd-agent run interactive experiment.yaml
```

The agent should use this for:

- debugging
- smoke tests
- validating dataset paths
- checking memory usage
- verifying model/config correctness

Interactive and batch execution must use the exact same resolved config.

Do not derive batch jobs from shell history.

---

# 12. Batch Execution

Support:

```bash
orcd-agent run submit experiment.yaml
```

Generate a reproducible Slurm script from the resolved configuration.

Support:

```bash
orcd-agent run submit experiment.yaml --dry-run --json
```

The JSON response should include:

```json
{
  "command": "...",
  "sbatch_path": "...",
  "resources": {...},
  "resolved_config": "..."
}
```

---

# 13. Interactive → Batch Promotion

Support:

```bash
orcd-agent promote <run-id> --json
```

Given a successful interactive run:

1. Load its resolved config.
2. Load actual resource usage.
3. Preserve scientific configuration exactly.
4. Adjust only execution/resource fields.
5. Generate a batch-ready configuration.
6. Return a structured diff.

Example:

```json
{
  "source_run": "...",
  "scientific_config_changed": false,
  "resource_changes": {
    "time": {
      "old": "04:00:00",
      "new": "03:30:00"
    },
    "memory": {
      "old": "64G",
      "new": "40G"
    }
  }
}
```

Never silently change:

- dataset
- split
- augmentation
- model
- learning rate
- batch size
- seed

---

# 14. Similar Run Retrieval

Implement:

```bash
orcd-agent runs similar \
  --experiment experiment.yaml \
  --json
```

Compare using weighted metadata.

Priority:

```text
same model
same dataset
same dataset variant
same augmentation
same split
same batch size
same GPU type
same precision
same sequence length
```

Return:

```json
{
  "matches": [
    {
      "run_id": "...",
      "similarity": 0.94,
      "differences": {
        "seed": [42, 43]
      },
      "runtime_seconds": 10320
    }
  ]
}
```

Start with deterministic matching, not embeddings.

---

# 15. Resource Estimation

Implement:

```bash
orcd-agent estimate experiment.yaml --json
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

- prefer medians
- report sample count
- report range
- clearly identify differences
- do not extrapolate across GPU types initially
- return `insufficient_history` when necessary

---

# 16. Agent Memory Behavior

The coding agent should treat the project runtime as persistent operational memory.

Add this behavior to agent instructions:

```markdown
When `.orcd/project.yaml` exists:

- Query `orcd-agent context --json` before making assumptions.
- Query dataset metadata before creating new data paths.
- Query similar runs before estimating runtime or resources.
- Reuse established project conventions.
- Do not invent new storage layouts unless necessary.
- Record new experiment variants instead of overwriting previous ones.
- Use interactive execution for new/uncertain configurations.
- Promote validated workloads to batch execution.
```

---

# 17. Experiment Organization

Support common ML workflows naturally:

```text
baseline
dataset comparison
split comparison
augmentation ablation
hyperparameter search
seed replication
model ablation
objective ablation
precision comparison
GPU comparison
scaling experiments
```

Do not create special-case code for each.

They should all be expressible through experiment metadata.

Example:

```yaml
metadata:
  study: augmentation_ablation
  condition: foodb_10x
```

---

# 18. Optional Study Grouping

Allow runs to belong to a study:

```yaml
study:
  name: smiles_augmentation_ablation
```

Then support:

```bash
orcd-agent runs study smiles_augmentation_ablation --json
```

This lets the agent reason about related experiments without requiring MLflow.

Keep this lightweight.

---

# 19. Sweeps

Design for later support:

```yaml
sweep:
  batch_size: [128, 256]
  learning_rate: [1e-3, 1e-4]
  seed: [1, 2, 3]
```

Future command:

```bash
orcd-agent sweep experiment.yaml
```

Generate Slurm arrays.

Do not implement in the first milestone.

---

# 20. Standardized Metadata Schema

Use common core fields:

```text
dataset
dataset_variant
split
augmentation
model
batch_size
learning_rate
precision
seed
GPU
number of GPUs
runtime
memory
git commit
Slurm job ID
```

Allow arbitrary extension fields.

Never require the tool to understand every research-specific hyperparameter.

---

# 21. Avoid Duplicating Experiment Trackers

This system should not replace:

- W&B
- MLflow
- TensorBoard

Its responsibility is:

```text
project structure
+
HPC execution
+
dataset/storage awareness
+
resource history
+
agent memory
```

If W&B/MLflow exists, optionally record:

```yaml
tracking:
  provider: wandb
  run_id: ...
```

but do not make it required.

---

# 22. Machine-Readable First

Every important command should support:

```bash
--json
```

Examples:

```bash
orcd-agent context --json

orcd-agent datasets show foodb --json

orcd-agent runs similar --experiment x.yaml --json

orcd-agent estimate x.yaml --json

orcd-agent promote run-id --json
```

CLI text is for humans.

JSON is the primary agent interface.

---

# 23. Implementation Order

## Phase 1 — Persistent project knowledge

Implement:

```text
project discovery
project.yaml
typed schemas
dataset registry
experiment schema
context --json
```

## Phase 2 — Run provenance

Implement:

```text
resolved experiment config
run IDs
run.yaml
git metadata
dataset metadata
resource metadata
```

## Phase 3 — Execution

Implement:

```text
interactive backend
Slurm batch backend
dry-run
same resolved config for both
```

## Phase 4 — Agent reasoning support

Implement:

```text
run list/show
similar-run matching
resource estimate
project/study queries
```

## Phase 5 — Promotion

Implement:

```text
interactive → batch promotion
resource diff
batch-ready config
```

## Later

```text
sweeps / Slurm arrays
dataset staging
W&B/MLflow integration
advanced runtime prediction
```

---

# 24. MVP Acceptance Scenario

Suppose the project previously ran:

```text
FoodDB
10× SMILES augmentation
batch size 256
H200
runtime ≈ 3h
```

The coding agent is asked:

> Try the same experiment with 5× augmentation and batch size 512.

The desired workflow is:

```bash
orcd-agent context --json
```

Agent discovers project conventions.

Then:

```bash
orcd-agent datasets list --json
```

Agent finds existing dataset variants.

It creates:

```yaml
dataset:
  variant: foodb_5x

training:
  batch_size: 512
```

Then queries:

```bash
orcd-agent runs similar \
  --experiment new_experiment.yaml \
  --json
```

It learns the closest previous runs used:

```text
foodb_10x
batch_size 256
H200
~3 hours
```

Then:

```bash
orcd-agent estimate new_experiment.yaml --json
```

If history is insufficient, the tool should say so rather than fabricate an estimate.

Agent performs:

```bash
orcd-agent run interactive new_experiment.yaml
```

After validating it:

```bash
orcd-agent promote <run-id> --json
```

Then submits the batch version.

The agent should be able to execute this workflow without relying on previous chat history.

---

# Core Objective

The project runtime should function as:

> **Persistent, structured project memory for coding agents operating ML workloads on HPC.**

It should let an agent answer:

```text
What datasets already exist?
Which split should I use?
Where should outputs go?
What environment does this project use?
What experiments have already been tried?
What changed between those experiments?
How long did similar runs take?
What resources did they actually use?
Has this configuration already been tested?
Can I safely promote this interactive run to batch?
```

without requiring the user to repeatedly explain the project.
