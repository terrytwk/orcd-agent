from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTEXT = ROOT / "bin" / "orcd-context"


def run_context(extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(extra_env or {})
    env["PATH"] = "/usr/bin:/bin"
    return subprocess.run([sys.executable, str(CONTEXT)], env=env, text=True, capture_output=True, check=True)


def test_no_slurm_defaults_conservatively() -> None:
    env = {key: "" for key in os.environ if key.startswith("SLURM_")}
    result = run_context(env)
    assert "Node type:" in result.stdout
    assert "Slurm job: not detected" in result.stdout
    assert "Warning: No Slurm allocation was detected" in result.stdout


def test_simulated_slurm_allocation() -> None:
    result = run_context(
        {
            "SLURM_JOB_ID": "123",
            "SLURM_JOB_PARTITION": "sched_mit_test",
            "SLURM_CPUS_ON_NODE": "8",
            "SLURM_GPUS": "1",
            "SLURM_MEM_PER_NODE": "32G",
        }
    )
    assert "Node type: COMPUTE" in result.stdout
    assert "Slurm job: 123" in result.stdout
    assert "Partition: sched_mit_test" in result.stdout
    assert "GPUs: 1" in result.stdout


def test_missing_module_command_is_reported() -> None:
    result = run_context()
    assert "module command not available" in result.stdout


def test_context_source_has_no_expensive_filesystem_operations() -> None:
    source = CONTEXT.read_text(encoding="utf-8")
    forbidden_execution_shapes = [
        'subprocess.run(["find"',
        'subprocess.run(["grep"',
        'subprocess.run(["du"',
        "subprocess.run('find",
        "subprocess.run('grep",
        "subprocess.run('du",
    ]
    assert not any(shape in source for shape in forbidden_execution_shapes)
