import unittest

from packages.benchmark.importers.custom import DummyBenchmarkImporter
from packages.benchmark.manager.facade import BenchmarkManager
from packages.benchmark.registry.memory import InMemoryRegistry
from packages.benchmark.validation import MetadataValidator, RegistryValidator, SchemaValidator


class TestBenchmarkFoundation(unittest.TestCase):
    def test_custom_benchmark_lifecycle(self):
        registry = InMemoryRegistry()
        validators = [SchemaValidator(), MetadataValidator(), RegistryValidator(registry)]

        class DummyLoader:
            def load(self, source):
                return DummyBenchmarkImporter().import_data(source)

        manager = BenchmarkManager(
            registry=registry, validators=validators, loaders={"dummy": DummyLoader()}
        )

        # Load and register
        benchmark = manager.load_and_register(source="dummy_source", format="dummy")

        # Verify Registration
        self.assertEqual(benchmark.metadata.benchmark_id, "dummy-bench-001")
        self.assertEqual(len(benchmark.tasks), 3)
        self.assertEqual(benchmark.tasks[0].title, "Addition")

        # Search
        results = manager.search_benchmarks({"difficulty": "easy"})
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].metadata.name, "Dummy Architecture Benchmark")


if __name__ == "__main__":
    unittest.main()
