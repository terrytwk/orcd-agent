#!/bin/bash
#
# Adjust partition, GPU count, CPU count, memory, and runtime for your workload.
#SBATCH --job-name=orcd-gpu-job
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=01:00:00

set -euo pipefail

module load miniforge

python script.py
