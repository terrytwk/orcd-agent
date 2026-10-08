#!/bin/bash
#
# Adjust partition, CPU count, memory, and runtime for your workload.
#SBATCH --job-name=orcd-cpu-job
#SBATCH --partition=standard
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=01:00:00

set -euo pipefail

module load miniforge

python script.py
