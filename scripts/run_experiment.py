import sys
import os
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from packages.experiments.models import ExperimentConfig
from packages.experiments.runner import ExperimentRunner

def main():
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
        
    parser = argparse.ArgumentParser(description="Run an Atlas Experiment")
    parser.add_argument("--dataset", type=str, required=False, help="Dataset (e.g. HumanEval or MBPP)")
    parser.add_argument("--provider", type=str, default="ollama", help="Provider")
    parser.add_argument("--model", type=str, default="qwen2.5-coder:1.5b", help="Model name")
    parser.add_argument("--limit", type=int, default=None, help="Max tasks to run")
    parser.add_argument("--prompt", type=str, default="v3", help="Prompt version")
    parser.add_argument("--temperature", type=float, default=0.0, help="Temperature")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--resume", type=str, default=None, help="Resume an experiment by ID")
    
    # Lineage tracking
    parser.add_argument("--parent", type=str, default=None, help="Parent experiment ID")
    parser.add_argument("--change", type=str, default=None, help="What changed in this experiment")
    parser.add_argument("--reason", type=str, default=None, help="Reason for the change")
    
    args = parser.parse_args()
    runner = ExperimentRunner()
    
    if args.resume:
        print(f"Resuming experiment {args.resume}...")
        runner.resume(args.resume)
        exp_id = args.resume
    else:
        if not args.dataset:
            parser.error("--dataset is required when not using --resume")
            
        # Collect metadata
        from packages.experiments.metadata import collect_metadata
        metadata = collect_metadata(args.model)
        
        config = ExperimentConfig(
            dataset=args.dataset,
            provider=args.provider,
            model=args.model,
            prompt_version=args.prompt,
            max_tasks=args.limit,
            temperature=args.temperature,
            seed=args.seed,
            parent_experiment=args.parent,
            lineage_change=args.change,
            lineage_reason=args.reason,
            **metadata
        )
        
        exp_id = runner.run(config)
        
    print(f"\nExperiment {exp_id} results are available in results/experiments/{exp_id}/")

if __name__ == "__main__":
    main()
