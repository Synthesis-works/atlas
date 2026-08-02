import argparse
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from packages.research.datasets.experiment_loader import ExperimentLoader
from packages.research.statistics.logic_analyzer import LogicAnalyzer
from packages.research.visualization.charts import ChartGenerator


def main():
    parser = argparse.ArgumentParser(description="Analyze logic errors for an experiment")
    parser.add_argument("--job", type=str, required=True, help="Experiment ID")
    parser.add_argument(
        "--out", type=str, default="logic_errors_report.md", help="Output markdown file"
    )

    args = parser.parse_args()

    loader = ExperimentLoader()
    try:
        failures = loader.load_failures(args.job)
    except FileNotFoundError as e:
        print(str(e))
        return

    analyzer = LogicAnalyzer()

    # We only want to analyze logic/runtime errors
    logic_errors = [
        f
        for f in failures
        if f.get("evaluation_status") == "FAIL" or f.get("execution_status") == "ERROR"
    ]

    if not logic_errors:
        print(f"No logic errors found for job {args.job}")
        return

    print(f"Analyzing {len(logic_errors)} logic errors...")

    categories = []
    for task in logic_errors:
        cat = analyzer.analyze(task)
        categories.append(cat)

    counts = dict(Counter(categories))

    # Generate visualization
    charts = ChartGenerator(output_dir=os.path.dirname(args.out) or ".")
    charts.plot_failure_pie(counts, filename="logic_error_pie.png")

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(f"# Logic Error Analysis for {args.job}\n\n")
        f.write(f"**Total Logic/Runtime Errors:** {len(logic_errors)}\n\n")
        f.write("![Logic Error Breakdown](logic_error_pie.png)\n\n")

        f.write("## Breakdown\n")
        for cat, count in sorted(counts.items(), key=lambda x: x[1], reverse=True):
            f.write(f"- **{cat}**: {count}\n")

    print(f"Logic errors report saved to {args.out}")


if __name__ == "__main__":
    main()
