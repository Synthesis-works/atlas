import sys
import os
import json
from datetime import datetime

# Add workspace root to sys.path
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

def main():
    # Save the log file strictly in the atlas folder (project root)
    log_file_path = os.path.join(os.path.dirname(__file__), '..', 'qwen_verification_logs.txt')
    log_file_path = os.path.abspath(log_file_path)
    
    with open(log_file_path, "w", encoding="utf-8") as log_file:
        def log_print(text):
            print(text)
            log_file.write(text + "\n")
            log_file.flush()

        log_print("1. Loading benchmark manager...")
        registry = InMemoryRegistry()
        validators = [SchemaValidator(), MetadataValidator(), RegistryValidator(registry)]
        loaders = {"yaml": YAMLLoader()}
        manager = BenchmarkManager(registry, validators, loaders)
        
        adapter = ProviderAdapter()
        model = DEFAULT_OLLAMA_MODEL
        log_print(f"Connecting to Ollama... using model: {model}\n")

        custom_benchmarks_dir = os.path.join("benchmarks", "coding", "custom")
        yaml_files = [f for f in os.listdir(custom_benchmarks_dir) if f.endswith('.yaml')]
        
        for yaml_file in yaml_files:
            log_print(f"---------------------------------------------------")
            log_print(f"Processing Benchmark: {yaml_file}")
            benchmark_path = os.path.join(custom_benchmarks_dir, yaml_file)
            
            try:
                benchmark = manager.load_and_register(source=benchmark_path, format="yaml")
                task = benchmark.tasks[0]
                
                log_print(f"Task ID: {task.task_id}")
                log_print(f"Input:\n{task.input}")
                
                prompt = PromptBuilder.build_from_task(task)
                
                log_print("Running Qwen generation...")
                response = adapter.generate(provider="ollama", model=model, prompt=prompt)
                
                log_print(f"Response:\n{response.response}")
                log_print(f"Latency: {response.latency_ms} ms")
                
                # Save JSON
                date_str = datetime.now().strftime("%Y-%m-%d")
                benchmark_id = benchmark.metadata.benchmark_id
                save_dir = os.path.join("results", date_str, benchmark_id, "qwen")
                os.makedirs(save_dir, exist_ok=True)
                save_path = os.path.join(save_dir, "response.json")
                
                output_json = {
                    "benchmark": benchmark_id,
                    "model": model,
                    "response": response.response,
                    "runtime": f"{response.latency_ms / 1000.0}s",
                    "full_response": response.model_dump()
                }
                
                with open(save_path, "w", encoding="utf-8") as f:
                    json.dump(output_json, f, indent=2)
                log_print(f"Saved response JSON to {save_path}\n")
                
            except Exception as e:
                log_print(f"Error processing {yaml_file}: {e}\n")

    print(f"\nAll logs have been written to: {log_file_path}")

if __name__ == "__main__":
    main()
