import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np

from packages.embedding.ollama import OllamaEmbeddingProvider
from packages.research.clustering.semantic_cluster import SemanticClusterer
from packages.research.datasets.experiment_loader import ExperimentLoader
from packages.research.visualization.charts import ChartGenerator


def main():
    parser = argparse.ArgumentParser(description="Cluster failures semantically")
    parser.add_argument("--job", type=str, required=True, help="Experiment ID")
    parser.add_argument("--out", type=str, default="cluster_report.md", help="Output markdown file")

    args = parser.parse_args()

    loader = ExperimentLoader()
    try:
        failures = loader.load_failures(args.job)
    except FileNotFoundError as e:
        print(str(e))
        return

    if not failures:
        print(f"No failures found for job {args.job}")
        return

    print(f"Clustering {len(failures)} failures...")

    provider = OllamaEmbeddingProvider()
    clusterer = SemanticClusterer(provider)
    result = clusterer.cluster_tasks(failures, text_key="prompt")

    # Generate visualization
    charts = ChartGenerator(output_dir=os.path.dirname(args.out) or ".")

    embeddings_2d = np.array(result.get("embeddings_2d", []))
    labels = result.get("labels", [])
    if len(embeddings_2d) > 0 and len(labels) > 0:
        charts.plot_cluster_scatter(embeddings_2d, labels, filename="cluster_scatter.png")

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(f"# Semantic Clustering Report for {args.job}\n\n")
        f.write(f"**Total Failures Clustered:** {len(failures)}\n")
        f.write(f"**Optimal Clusters (K):** {result.get('best_k')}\n")
        f.write(f"**Silhouette Score:** {result.get('silhouette_score'):.3f}\n\n")
        f.write("![Cluster Scatter](cluster_scatter.png)\n\n")

        for name, info in result.get("clusters", {}).items():
            f.write(f"## {name}\n")
            f.write(f"- **Task Count:** {info['task_count']}\n")
            f.write(f"- **Keywords:** {', '.join(info['keywords'])}\n")
            f.write(f"- **Representative Task:** {info['representative_task']}\n\n")

    print(f"Cluster report saved to {args.out}")


if __name__ == "__main__":
    main()
