from packages.research.datasets.experiment_loader import ExperimentLoader
from packages.research.statistics.confidence import format_ci


class PromptComparator:
    def __init__(self, loader: ExperimentLoader):
        self.loader = loader

    def generate_comparison_markdown(self, exp_ids: list[str]) -> str:
        headers = [
            "Metric",
        ] + [exp_id for exp_id in exp_ids]

        # We will collect data
        summaries = {}
        for exp_id in exp_ids:
            try:
                summaries[exp_id] = self.loader.load_summary(exp_id)
            except Exception as e:
                print(f"Warning: Could not load summary for {exp_id}: {e}")

        metrics = [
            ("Pass@1 (95% CI)", lambda s: format_ci(s.get("passed", 0), s.get("total_tasks", 1))),
            ("Prompt Compliance", lambda s: f"{s.get('prompt_compliance_rate', 0) * 100:.1f}%"),
            ("Avg Generation Latency", lambda s: f"{s.get('average_generation_latency_ms', 0)} ms"),
            ("Avg Execution Latency", lambda s: f"{s.get('average_execution_latency_ms', 0)} ms"),
            ("Avg Prompt Length", lambda s: f"{s.get('average_prompt_tokens', 0)} tokens"),
            ("Avg Completion Length", lambda s: f"{s.get('average_completion_tokens', 0)} tokens"),
            ("Repairable Errors", lambda s: str(s.get("repairable_failures", 0))),
            ("Unrepairable Errors", lambda s: str(s.get("unrepairable_failures", 0))),
            (
                "Extraction Failures",
                lambda s: str(s.get("failure_breakdown", {}).get("extraction", 0)),
            ),
            ("Logic Errors", lambda s: str(s.get("failure_breakdown", {}).get("logic", 0))),
            ("Runtime Errors", lambda s: str(s.get("failure_breakdown", {}).get("runtime", 0))),
            ("Syntax Errors", lambda s: str(s.get("failure_breakdown", {}).get("syntax", 0))),
        ]

        md = f"| {' | '.join(headers)} |\n"
        md += f"| {' | '.join(['---'] * len(headers))} |\n"

        for metric_name, extractor in metrics:
            row = [metric_name]
            for exp_id in exp_ids:
                if exp_id in summaries:
                    row.append(extractor(summaries[exp_id]))
                else:
                    row.append("N/A")
            md += f"| {' | '.join(row)} |\n"

        return md
