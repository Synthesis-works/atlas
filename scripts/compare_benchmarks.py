import argparse
import sys
import os
import json
import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from packages.experiments.registry import ExperimentRegistry

def generate_comparison(exp1_id: str, exp2_id: str, output_file: str):
    registry = ExperimentRegistry()
    all_exps = registry.get_all()
    
    exp1_data = next((e for e in all_exps if e["id"] == exp1_id), None)
    exp2_data = next((e for e in all_exps if e["id"] == exp2_id), None)
    
    if not exp1_data:
        print(f"Experiment {exp1_id} not found.")
        return
    if not exp2_data:
        print(f"Experiment {exp2_id} not found.")
        return
        
    m1 = exp1_data.get("metrics", {})
    m2 = exp2_data.get("metrics", {})
    
    ds1 = exp1_data.get("config", {}).get("dataset", "Dataset 1")
    ds2 = exp2_data.get("config", {}).get("dataset", "Dataset 2")
    
    # Calculate some stats not directly in metrics if needed, but registry might have them
    def get_stat(metrics, key, default=0):
        val = metrics.get(key, default)
        if isinstance(val, float):
            return f"{val:.1f}"
        return str(val)
        
    report = f"""# Cross-Benchmark Comparison
Generated on: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Comparing {ds1} ({exp1_id}) vs {ds2} ({exp2_id}).

| Metric | {ds1.capitalize()} | {ds2.capitalize()} |
| --- | ---: | ---: |
| Pass@1 | {get_stat(m1, 'pass_at_1')}% | {get_stat(m2, 'pass_at_1')}% |
| Runtime errors | {get_stat(m1, 'runtime_errors')} | {get_stat(m2, 'runtime_errors')} |
| Logic errors | {get_stat(m1, 'logic_errors')} | {get_stat(m2, 'logic_errors')} |
| Syntax errors | {get_stat(m1, 'syntax_errors')} | {get_stat(m2, 'syntax_errors')} |
| Extraction failures | {get_stat(m1, 'extraction_failures')} | {get_stat(m2, 'extraction_failures')} |
| Avg latency | {get_stat(m1, 'avg_generation_latency_ms')} ms | {get_stat(m2, 'avg_generation_latency_ms')} ms |

## Notes
- This comparison gives insights into whether performance generalizes across benchmarks.
"""
    
    os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else '.', exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(report)
        
    print(f"Comparison report saved to {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Compare two benchmark experiments")
    parser.add_argument("--exp1", type=str, required=True, help="First experiment ID (e.g. humaneval)")
    parser.add_argument("--exp2", type=str, required=True, help="Second experiment ID (e.g. mbpp)")
    parser.add_argument("--out", type=str, default="comparison/humaneval_vs_mbpp.md", help="Output file path")
    args = parser.parse_args()
    
    generate_comparison(args.exp1, args.exp2, args.out)

if __name__ == "__main__":
    main()
