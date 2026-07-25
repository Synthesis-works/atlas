import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from packages.research.comparison.prompt_comparison import PromptComparator
from packages.research.datasets.experiment_loader import ExperimentLoader


def main():
    parser = argparse.ArgumentParser(description="Compare multiple prompt experiments")
    parser.add_argument("--jobs", nargs="+", required=True, help="List of exp_ids to compare")
    parser.add_argument(
        "--out", type=str, default="prompt_comparison.md", help="Output markdown file"
    )

    args = parser.parse_args()

    from packages.research.visualization.charts import ChartGenerator

    loader = ExperimentLoader()
    comparator = PromptComparator(loader)

    md_content = comparator.generate_comparison_markdown(args.jobs)

    # Also generate the prompt_comparison.png
    charts = ChartGenerator(output_dir=os.path.dirname(args.out) or ".")
    pass_rates = []
    for exp_id in args.jobs:
        try:
            s = loader.load_summary(exp_id)
            pass_rates.append((s.get("passed", 0) / max(s.get("total_tasks", 1), 1)) * 100)
        except Exception:
            pass_rates.append(0.0)

    charts.plot_prompt_comparison(args.jobs, pass_rates)

    with open(args.out, "w", encoding="utf-8") as f:
        f.write("# Prompt Comparison Report\n\n")
        f.write("![Prompt Comparison](prompt_comparison.png)\n\n")
        f.write(md_content)

    print(f"Comparison report saved to {args.out}")
    print("\n" + md_content)


if __name__ == "__main__":
    main()
