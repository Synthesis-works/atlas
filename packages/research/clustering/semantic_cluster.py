import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.feature_extraction.text import TfidfVectorizer
from typing import List, Dict, Any
from packages.embedding.base import BaseEmbeddingProvider

class SemanticClusterer:
    def __init__(self, embedding_provider: BaseEmbeddingProvider):
        self.embedding_provider = embedding_provider
        
    def cluster_tasks(self, tasks: List[Dict[str, Any]], text_key: str = "prompt") -> Dict[str, Any]:
        """
        Clusters a list of tasks (e.g. failed tasks) dynamically evaluating K=4..8.
        Returns a dict with cluster assignments, labels, and keywords.
        """
        texts = []
        task_ids = []
        for t in tasks:
            # Safely get the text to embed
            val = t.get(text_key, "")
            if not val and "task_id" in t:
                # maybe prompt is not in the json directly, use task_id as fallback or we assume prompt is passed
                pass
            texts.append(val if val else t.get("task_id", ""))
            task_ids.append(t.get("task_id", "unknown"))
            
        if not texts:
            return {}
            
        # 1. Embed
        embeddings = self.embedding_provider.embed_many(texts)
        X = np.array(embeddings)
        
        # 2. Find best K
        best_k = 1
        best_score = -1.0
        best_labels = np.zeros(len(texts), dtype=int)
        
        min_k = min(4, len(texts) - 1)
        max_k = min(8, len(texts) - 1)
        
        if min_k >= 2:
            for k in range(min_k, max_k + 1):
                kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
                labels = kmeans.fit_predict(X)
                score = silhouette_score(X, labels)
                if score > best_score:
                    best_score = score
                    best_k = k
                    best_labels = labels
        else:
            # Not enough data to cluster
            best_labels = np.zeros(len(texts), dtype=int)
            best_k = 1
            
        # Re-fit with best K to get centroids
        kmeans = KMeans(n_clusters=best_k, random_state=42, n_init=10)
        best_labels = kmeans.fit_predict(X)
        centroids = kmeans.cluster_centers_
        
        # 3. TF-IDF for Keywords
        vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
        try:
            tfidf_matrix = vectorizer.fit_transform(texts)
            feature_names = vectorizer.get_feature_names_out()
        except ValueError:
            feature_names = []
            
        clusters_info = {}
        
        for k in range(best_k):
            # Tasks in this cluster
            idx = np.where(best_labels == k)[0]
            cluster_task_ids = [task_ids[i] for i in idx]
            cluster_texts = [texts[i] for i in idx]
            
            # Keywords
            keywords = []
            if len(feature_names) > 0 and len(idx) > 0:
                # Average TF-IDF for the cluster
                avg_tfidf = np.asarray(tfidf_matrix[idx].mean(axis=0)).flatten()
                top_indices = avg_tfidf.argsort()[-5:][::-1]
                keywords = [feature_names[i] for i in top_indices]
                
            # Representative Task (Closest to centroid)
            centroid = centroids[k]
            dists = np.linalg.norm(X[idx] - centroid, axis=1)
            repr_idx = idx[np.argmin(dists)]
            repr_task_id = task_ids[repr_idx]
            
            clusters_info[f"Cluster_{k}"] = {
                "task_count": len(cluster_task_ids),
                "tasks": cluster_task_ids,
                "keywords": keywords,
                "representative_task": repr_task_id
            }
            
        from sklearn.decomposition import PCA
        pca = PCA(n_components=2)
        embeddings_2d = pca.fit_transform(X).tolist() if len(X) >= 2 else X[:, :2].tolist()
        
        return {
            "best_k": best_k,
            "silhouette_score": best_score,
            "clusters": clusters_info,
            "embeddings_2d": embeddings_2d,
            "labels": best_labels.tolist()
        }
