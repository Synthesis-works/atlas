import sys
import os

# Add workspace root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from packages.benchmark.registry.memory import InMemoryRegistry
from packages.benchmark.validation.schema import SchemaValidator
from packages.benchmark.validation.metadata import MetadataValidator
from packages.benchmark.validation.registry import RegistryValidator
from packages.benchmark.loader.yaml_loader import YAMLLoader
from packages.benchmark.manager.facade import BenchmarkManager

def main():
    registry = InMemoryRegistry()
    validators = [
        SchemaValidator(),
        MetadataValidator(),
        RegistryValidator(registry)
    ]
    loaders = {
        "yaml": YAMLLoader()
    }
    
    manager = BenchmarkManager(registry, validators, loaders)
    
    benchmark_dir = os.path.join("benchmarks", "coding", "custom")
    files = [
        "reverse_string.yaml",
        "palindrome.yaml",
        "fizzbuzz.yaml",
        "fibonacci.yaml",
        "binary_search.yaml"
    ]
    
    print("1. Loading, Validating, and Registering Benchmarks...")
    for f in files:
        path = os.path.join(benchmark_dir, f)
        try:
            b = manager.load_and_register(source=path, format="yaml")
            print(f"  [OK] Registered: {b.metadata.name} (ID: {b.metadata.benchmark_id})")
        except Exception as e:
            print(f"  [ERROR] Failed to load {f}: {e}")

    print("\n2. Searching Benchmarks by Category (coding)...")
    results = manager.search_benchmarks({"category": "coding"})
    print(f"  Found {len(results)} coding benchmarks.")

    print("\n3. Searching Benchmarks by Difficulty (easy)...")
    results = manager.search_benchmarks({"difficulty": "easy"})
    for r in results:
        print(f"  - {r.metadata.name} (ID: {r.metadata.benchmark_id})")

    print("\n4. Searching Benchmarks by Difficulty (medium)...")
    results = manager.search_benchmarks({"difficulty": "medium"})
    for r in results:
        print(f"  - {r.metadata.name} (ID: {r.metadata.benchmark_id})")

    print("\n5. Confirming Full Lifecycle...")
    print("  Registry currently holds:")
    for b in manager.search_benchmarks():
        print(f"  - {b.metadata.benchmark_id}: {b.metadata.name} v{b.metadata.version} with {len(b.tasks)} tasks.")

if __name__ == "__main__":
    main()
