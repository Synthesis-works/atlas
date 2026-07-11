# Atlas Benchmarks (5-Minute Setup)

Atlas is a robust evaluation orchestrator designed to run code generation benchmarks cleanly, automatically repair models, and cleanly persist experimental state.

## 1. Setup

Start your Ollama server with your models folder:
```powershell
$env:OLLAMA_MODELS="D:\ollama_models\models"; ollama serve
```

Ensure dependencies are installed:
```powershell
pip install -r requirements.txt
```

## 2. Run HumanEval

Run a zero-shot prompt evaluation with HumanEval on Qwen 2.5 Coder 1.5B (using prompt V3):

```powershell
py scripts/run_experiment.py `
    --dataset humaneval `
    --provider ollama `
    --model qwen2.5-coder:1.5b `
    --prompt v3
```

You can optionally test on a small subset of tasks with `--limit 10`:
```powershell
py scripts/run_experiment.py --dataset humaneval --prompt v3 --limit 10
```

## 3. Run MBPP

MBPP is natively supported. Run it exactly the same way:

```powershell
py scripts/run_experiment.py `
    --dataset mbpp `
    --provider ollama `
    --model qwen2.5-coder:1.5b `
    --prompt v3
```

## 4. Resume an Experiment

If you press `Ctrl+C` or the process crashes, Atlas automatically saves a checkpoint. To resume exactly where you left off:

```powershell
py scripts/resume_experiment.py --job exp-mbpp-xxxxxx
```

Atlas will load the `checkpoint.json` and continue execution.

## 5. Reports and Analysis

### Generate a Single Experiment Report
Generate a detailed Markdown/PDF summary for a single completed experiment:
```powershell
py scripts/generate_report.py --job exp-humaneval-xxxxxx
```

### Compare Experiments (e.g., HumanEval vs MBPP)
Generate a comparative report between two different runs to compare pass rates, prompt compliance, and logic errors side-by-side:
```powershell
py scripts/generate_comparative_report.py --he exp-humaneval-xxxxxx --mbpp exp-mbpp-yyyyyy
```

### Compare Prompts
To compare how prompt wording affected logic errors (e.g. V1 vs V3):
```powershell
py scripts/compare_prompts.py --exp1 exp-humaneval-v1xxxx --exp2 exp-humaneval-v3xxxx
```

## 6. Prompt Genealogy

Prompts are stored in `prompts/`.
**Rule**: Do NOT modify existing versions (`v1.md`, `v2.md`, etc.). If you want to change a prompt, duplicate it as a new version (`v4.md`) and run it. This guarantees exact reproducibility for all historical experiments.
