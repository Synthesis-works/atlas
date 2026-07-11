import argparse
import json
import os
import datetime
from packages.experiments.registry import ExperimentRegistry
from packages.research.insights.generator import InsightGenerator

def generate_report(exp_id: str, output_file: str):
    registry = ExperimentRegistry()
    all_exps = registry.get_all()
    
    exp_data = next((e for e in all_exps if e["id"] == exp_id), None)
    if not exp_data:
        print(f"Experiment {exp_id} not found in registry.")
        return
        
    config = exp_data.get("config", {})
    metrics = exp_data.get("metrics", {})
    
    print(f"Generating insights for {exp_id}...")
    insight_gen = InsightGenerator()
    insights = insight_gen.generate({"config": config, "metrics": metrics})
    
    report_md = f"""# Research Report: {exp_id}
Generated on: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 1. Experiment Lineage
* **Model**: {config.get("model")}
* **Dataset**: {config.get("dataset")}
* **Prompt Version**: {config.get("prompt_version")}
* **Parent Experiment**: {config.get("parent_experiment") or "None (Root)"}
* **Change**: {config.get("lineage_change") or "N/A"}
* **Reason**: {config.get("lineage_reason") or "N/A"}
* **Atlas Version**: {config.get("atlas_version")}

## 2. Quantitative Results
* **Pass@1**: {metrics.get("pass_at_1", 0):.1f}% ({metrics.get("passed_tasks", 0)}/{metrics.get("total_tasks", 0)})
* **Generation Latency (avg)**: {metrics.get("avg_generation_latency_ms", 0)} ms
* **Execution Latency (avg)**: {metrics.get("avg_execution_latency_ms", 0)} ms
* **Prompt Compliance**: {metrics.get("prompt_compliance", 0):.1f}%

## 3. AI Insights
{insights}

## 4. Failure Analysis
See clustering and logic analysis tools for detailed failure distributions.
"""

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(report_md)
        
    print(f"Report saved to {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Generate Research Report")
    parser.add_argument("--exp", type=str, required=True, help="Experiment ID to report on")
    parser.add_argument("--out", type=str, default="report.md", help="Output file path")
    args = parser.parse_args()
    
    generate_report(args.exp, args.out)

if __name__ == "__main__":
    main()
