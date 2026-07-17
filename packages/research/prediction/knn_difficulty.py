import numpy as np

class KNNDifficultyPredictor:
    """
    Computes difficulty score using k-NN embedding cosine similarity.
    Finds the k most similar tasks and averages their pass rates.
    """
    def __init__(self, registry_path: str = "results/experiments/registry.json", k: int = 5):
        self.k = k
        self.history = []
        
        # Load historical tasks from experiments
        # We need task embeddings and their pass status
        # Since we don't have embeddings pre-calculated in registry, we'd need to compute or load them.
        # For this skeleton, we'll simulate the embedding lookup if embeddings are not passed.
        pass

    def compute_difficulty(self, task_embedding: np.ndarray, historical_embeddings: np.ndarray, historical_pass_rates: np.ndarray) -> float:
        """
        Computes deterministic difficulty score [0, 1] using k-NN.
        1.0 means extremely difficult.
        """
        if len(historical_embeddings) == 0:
            return 0.5
            
        # Compute cosine similarity
        norm_task = np.linalg.norm(task_embedding)
        norm_history = np.linalg.norm(historical_embeddings, axis=1)
        
        # Avoid division by zero
        if norm_task == 0:
            norm_task = 1e-9
        norm_history[norm_history == 0] = 1e-9
            
        similarities = np.dot(historical_embeddings, task_embedding) / (norm_history * norm_task)
        
        # Get top k indices
        k_actual = min(self.k, len(similarities))
        top_k_indices = np.argsort(similarities)[-k_actual:]
        
        # Average pass rate of top k similar tasks
        avg_pass_rate = np.mean(historical_pass_rates[top_k_indices])
        
        # Inverse pass rate: lower pass rate = higher difficulty
        difficulty = 1.0 - avg_pass_rate
        
        return float(np.clip(difficulty, 0.0, 1.0))
