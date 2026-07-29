import argparse
import os
import sys
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def main():
    parser = argparse.ArgumentParser(description="Resume an Atlas Experiment")
    parser.add_argument("--job", type=str, required=True, help="Job ID to resume")
    args = parser.parse_args()

    base_dir = "results/experiments"
    exp_dir = os.path.join(base_dir, args.job)

    if not os.path.exists(exp_dir):
        print(f"Error: Experiment directory {exp_dir} not found.")
        sys.exit(1)

    from packages.experiments.runner import ExperimentRunner

    runner = ExperimentRunner(base_dir=base_dir)
    runner.resume(args.job)


if __name__ == "__main__":
    main()
