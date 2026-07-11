# Project Atlas

Project Atlas is an AI Evaluation Operating System built from scratch as a modular monorepo.

- **Organization:** [Synthesis-works](https://github.com/Synthesis-works)
- **Repository:** [atlas](https://github.com/Synthesis-works/atlas)

## Repository Structure

The monorepo follows the Atlas V1 Repository Architecture:

- `apps/` - Main frontend applications (e.g., `web/`, `landing/`, `docs-site/`)
- `services/` - Backend microservices (e.g., `auth/`, `execution/`, `evaluation/`)
- `packages/` - Reusable internal code and libraries (e.g., `database/`)
- `benchmarks/` - AI evaluation benchmarks
- `datasets/` - Raw and processed data
- `infrastructure/` - Deployment and hosting configuration
- `docker/` - Containerization files
- `scripts/` - Automation and setup utilities
- `docs/` - Project documentation (e.g., `scratchpad/`)
- `tests/` - System-wide testing
- `configs/` - Environment configurations
- `sdk/` - Future SDK development
- `cli/` - Future Command Line Interface
- `.github/` - CI/CD and repository automation
## Atlas Benchmark Framework v1.0

The benchmark module allows you to run robust, reproducible AI coding evaluations.

### Quick Start

Run an experiment on a dataset (e.g., HumanEval or MBPP) using a supported provider:

``powershell
# Run the first 10 HumanEval tasks using Ollama (local model)
py scripts/run_experiment.py --dataset humaneval --provider ollama --limit 10
``

To run all tasks, omit the --limit flag:
``powershell
py scripts/run_experiment.py --dataset humaneval --provider ollama --model qwen2.5-coder:1.5b --prompt v3
``

### Resume Experiments

Experiments are automatically checkpointed. If you stop an experiment (e.g., via Ctrl+C), you can safely resume it:

``powershell
py scripts/run_experiment.py --resume exp-humaneval-123456
``
Atlas will skip completed tasks and continue from where it left off.

### Generate Reports

Generate an exhaustive Markdown report from a completed experiment run:

``powershell
py scripts/generate_report.py --exp exp-humaneval-123456
``

### Compare Prompts (McNemar's Test)

Compare two runs of the same model with different prompt versions to see if the improvement is statistically significant:

``powershell
py scripts/mcnemar_test.py --exp1 exp-humaneval-111111 --exp2 exp-humaneval-222222
``

### Validate Providers

Before running a large benchmark, validate that your API credentials and setup are working:

``powershell
py scripts/validate_provider.py --provider gemini --model gemini-2.5-flash
py scripts/validate_provider.py --provider grok --model grok-2-1212
``
This runs a tiny 10-task test suite to verify generation, extraction, execution, and evaluation.
