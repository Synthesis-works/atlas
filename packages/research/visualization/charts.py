import os

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns


class ChartGenerator:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        # Use a nice default style
        sns.set_theme(style="whitegrid")

    def plot_failure_pie(self, breakdown: dict[str, int], filename="failure_pie.png"):
        labels = list(breakdown.keys())
        sizes = list(breakdown.values())

        # Filter out 0s
        labels = [l for l, s in zip(labels, sizes) if s > 0]
        sizes = [s for s in sizes if s > 0]

        if not sizes:
            return

        fig, ax = plt.subplots(figsize=(6, 6))
        ax.pie(
            sizes,
            labels=labels,
            autopct="%1.1f%%",
            startangle=90,
            colors=sns.color_palette("pastel"),
        )
        ax.axis("equal")
        plt.title("Failure Breakdown")
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, filename), dpi=300)
        plt.close()

    def plot_latency_histogram(self, latencies: list[int], filename="latency_histogram.png"):
        if not latencies:
            return

        fig, ax = plt.subplots(figsize=(8, 5))
        sns.histplot(latencies, bins=30, kde=True, ax=ax, color="skyblue")
        ax.set_xlabel("Latency (ms)")
        ax.set_ylabel("Count")
        ax.set_title("Execution Latency Distribution")
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, filename), dpi=300)
        plt.close()

    def plot_prompt_comparison(
        self, exp_ids: list[str], pass_rates: list[float], filename="prompt_comparison.png"
    ):
        fig, ax = plt.subplots(figsize=(8, 5))
        sns.barplot(x=exp_ids, y=pass_rates, palette="viridis", ax=ax)

        # Add values on top
        for i, v in enumerate(pass_rates):
            ax.text(i, v + 1, f"{v:.1f}%", ha="center", fontweight="bold")

        ax.set_ylim(0, max(100, max(pass_rates) + 10))
        ax.set_ylabel("Pass@1 (%)")
        ax.set_xlabel("Experiment")
        ax.set_title("Prompt Strategy Comparison")
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, filename), dpi=300)
        plt.close()

    def plot_cluster_scatter(
        self, embeddings_2d: np.ndarray, labels: list[int], filename="cluster_scatter.png"
    ):
        fig, ax = plt.subplots(figsize=(8, 6))
        scatter = ax.scatter(
            embeddings_2d[:, 0], embeddings_2d[:, 1], c=labels, cmap="Set1", alpha=0.7
        )
        legend1 = ax.legend(*scatter.legend_elements(), title="Clusters")
        ax.add_artist(legend1)
        ax.set_title("Semantic Clustering of Failures")
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, filename), dpi=300)
        plt.close()
