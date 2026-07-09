import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from packages.embedding.ollama import OllamaEmbeddingProvider
from packages.embedding.cache import CachedEmbeddingProvider
from packages.embedding.vector import cosine_similarity, distance

def main():
    print("Testing Embedding Layer with nomic-embed-text...")
    
    # Wrap Ollama with Cache
    provider = CachedEmbeddingProvider(OllamaEmbeddingProvider())
    
    texts = [
        "A benchmark to test string reversal capability.",
        "Write a python program to reverse a string.",
        "Calculate the 100th Fibonacci number."
    ]
    
    print("Fetching embeddings... (Should cache on disk)")
    vectors = provider.embed_many(texts)
    
    print("\nEmbeddings fetched and cached successfully.")
    print(f"Vector dimensions: {len(vectors[0])}")
    
    print("\nSemantic comparisons:")
    print(f"Text A: '{texts[0]}'")
    print(f"Text B: '{texts[1]}'")
    sim_ab = cosine_similarity(vectors[0], vectors[1])
    print(f"-> Similarity A to B: {sim_ab:.4f} (Distance: {distance(vectors[0], vectors[1]):.4f})")
    
    print(f"\nText A: '{texts[0]}'")
    print(f"Text C: '{texts[2]}'")
    sim_ac = cosine_similarity(vectors[0], vectors[2])
    print(f"-> Similarity A to C: {sim_ac:.4f} (Distance: {distance(vectors[0], vectors[2]):.4f})")

if __name__ == "__main__":
    main()
