import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from packages.benchmark.registry.memory import InMemoryRegistry
from packages.benchmark.validation.schema import SchemaValidator
from packages.benchmark.validation.metadata import MetadataValidator
from packages.benchmark.validation.registry import RegistryValidator
from packages.benchmark.loader.yaml_loader import YAMLLoader
from packages.benchmark.manager.facade import BenchmarkManager

from packages.llm.clients.adapter import ProviderAdapter
from packages.llm.prompt_builder import PromptBuilder
from packages.llm.config import DEFAULT_OLLAMA_MODEL

from packages.evaluation.manager import EvaluationManager
from packages.evaluation.results.result import EvaluationResult

def main():
    print("1. Loading benchmark manager...")
    registry = InMemoryRegistry()
    validators = [SchemaValidator(), MetadataValidator(), RegistryValidator(registry)]
    loaders = {"yaml": YAMLLoader()}
    manager = BenchmarkManager(registry, validators, loaders)
    
    adapter = ProviderAdapter()
    model = DEFAULT_OLLAMA_MODEL
    
    eval_manager = EvaluationManager()
    all_results = []

    custom_benchmarks_dir = os.path.join("benchmarks", "coding", "custom")
    yaml_files = [f for f in os.listdir(custom_benchmarks_dir) if f.endswith('.yaml')]
    
    date_str = datetime.now().strftime("%Y-%m-%d")

    for yaml_file in yaml_files:
        print(f"\n---------------------------------------------------")
        print(f"Processing Benchmark: {yaml_file}")
        benchmark_path = os.path.join(custom_benchmarks_dir, yaml_file)
        
        try:
            benchmark = manager.load_and_register(source=benchmark_path, format="yaml")
            task = benchmark.tasks[0]
            
            print(f"Task ID: {task.task_id}")
            prompt = PromptBuilder.build_from_task(task)
            
            print("Running LLM generation...")
            response = adapter.generate(provider="ollama", model=model, prompt=prompt)
            print(f"Latency: {response.latency_ms} ms")
            
            print("Evaluating response...")
            eval_result = eval_manager.run_evaluation(benchmark.metadata.benchmark_id, task, response)
            
            all_results.append(eval_result)
            print(f"Status: {eval_result.status.value}")
            print(f"Expected: {eval_result.expected}")
            print(f"Normalized Actual: {eval_result.normalized_output}")
            
            save_dir = os.path.join("results", date_str, benchmark.metadata.benchmark_id, "evaluation")
            os.makedirs(save_dir, exist_ok=True)
            save_path = os.path.join(save_dir, "eval_result.json")
            
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(eval_result.model_dump(), f, indent=2, default=str)
                
        except Exception as e:
            print(f"Error processing {yaml_file}: {e}")

    print("\n===================================================")
    print("FINAL METRICS")
    metrics = eval_manager.compute_metrics(all_results)
    print(json.dumps(metrics, indent=2))
    print("===================================================")

if __name__ == "__main__":
    main()
