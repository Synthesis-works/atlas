from typing import Any

import numpy as np

from packages.embedding.base import BaseEmbeddingProvider


class NearestNeighborSuccessFinder:
    def __init__(self, embedding_provider: BaseEmbeddingProvider):
        self.embedding_provider = embedding_provider
        self.success_embeddings = None
        self.success_tasks = []

    def build_index(self, success_tasks: list[dict[str, Any]], text_key: str = "prompt"):
        """
        Embeds successful tasks so they can be queried.
        """
        self.success_tasks = success_tasks
        if not success_tasks:
            self.success_embeddings = np.array([])
            return

        texts = [t.get(text_key, t.get("task_id", "")) for t in success_tasks]

        # embed
        embs = self.embedding_provider.embed_many(texts)
        self.success_embeddings = np.array(embs)

    def find_nearest_success(
        self, failed_task: dict[str, Any], text_key: str = "prompt"
    ) -> tuple[dict[str, Any], float]:
        """
        Finds the nearest passed task to the given failed task.
        Returns (task, distance)
        """
        if self.success_embeddings is None or len(self.success_embeddings) == 0:
            return None, float("inf")

        text = failed_task.get(text_key, failed_task.get("task_id", ""))
        emb = np.array(self.embedding_provider.embed(text))

        # Euclidean distance
        dists = np.linalg.norm(self.success_embeddings - emb, axis=1)
        best_idx = np.argmin(dists)

        return self.success_tasks[best_idx], dists[best_idx]
