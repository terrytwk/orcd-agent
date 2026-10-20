# ORCD Agent Instructions

Follow these rules when working on MIT ORCD systems.

## Safety Rules

- Never run expensive computation on login nodes. Use Slurm allocations or batch jobs for compute-heavy work.
- Never run unbounded filesystem-wide searches or scans, including:
  - `find /`
  - `grep -R /`
  - `du /`
- Restrict file searches to the current project unless a wider search is explicitly necessary.
- Do not run cluster-wide discovery commands unless the user asked for them and the command is known to be lightweight.

## Software And Environments

- Check available modules before installing software.
- For Python, check and load Miniforge first:

  ```bash
  module avail miniforge
  module load miniforge
  ```

- Respect existing user and project configuration before choosing environment or cache locations. If variables such as `HF_HOME`, `HF_HUB_CACHE`, `HF_DATASETS_CACHE`, `XDG_CACHE_HOME`, `TORCH_HOME`, `PIP_CACHE_DIR`, or conda/mamba cache/env settings are already set, treat them as intentional and preserve them in commands and Slurm scripts.
- Use project-local directories for project-specific virtual environments when appropriate, but do not move large reusable caches or downloaded models into the project directory unless the user asks.
- Avoid writing large temporary data into shared or home directories without checking quotas, project conventions, and existing user-configured cache locations.
- If no cache location is configured, prefer scratch or documented project storage for large temporary/reusable caches, and warn before writing large data into home, shared, or project directories.

## Slurm

- Use Slurm for computational workloads.
- Put environment and module setup inside Slurm scripts so jobs are reproducible.
- Preserve relevant user/project environment variables in Slurm scripts, especially cache and data locations such as `HF_HOME`, `XDG_CACHE_HOME`, and `TORCH_HOME`.
- Keep resource requests modest and explicit. Adjust partition, runtime, CPU count, memory, and GPU count for the job.

## ORCD Agent Tools

- Run `orcd-context` at the beginning of a session to understand whether you are on a login node or inside a Slurm allocation.
- If `orcd-context` reports no Slurm allocation, behave conservatively and avoid expensive commands.

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

The CLI is a convenience, not a requirement. Direct filesystem access is intentional:

```bash
rg "miniforge" ~/.orcd-agent/knowledge
cat ~/.orcd-agent/knowledge/software/python.md
```
