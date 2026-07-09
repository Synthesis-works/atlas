import json
import os
from packages.benchmark.registry.memory import InMemoryRegistry
from packages.benchmark.validation.schema import SchemaValidator
from packages.benchmark.validation.metadata import MetadataValidator
from packages.benchmark.validation.registry import RegistryValidator
from packages.benchmark.loader.yaml_loader import YAMLLoader
from packages.benchmark.manager.facade import BenchmarkManager
from packages.llm.prompt_builder import PromptBuilder
from packages.llm.clients.adapter import ProviderAdapter
from packages.evaluation.extractors.code_block import CodeBlockExtractor
from packages.runtime.models.execution_request import ExecutionRequest, ExecutionContext
from packages.runtime.manager.runtime_manager import RuntimeManager
from packages.evaluation.results.result import EvaluationResult

def main():
    print("--- Atlas Phase 5: Runtime Integration Test ---")
    
    # 1. Load Benchmark
    registry = InMemoryRegistry()
    validators = [SchemaValidator(), MetadataValidator(), RegistryValidator(registry)]
    loaders = {"yaml": YAMLLoader()}
    manager = BenchmarkManager(registry, validators, loaders)
    
    # Use load_and_register on the fizzbuzz yaml
    b = manager.load_and_register("benchmarks/coding/custom/fizzbuzz.yaml", "yaml")
    task = next(t for t in b.tasks if t.task_id == "task-fizzbuzz-1")
    print(f"[1] Loaded Task: {task.task_id}")
    
    # 2. Build Prompt
    prompt = PromptBuilder.build_from_task(task)
    print(f"[2] Built Prompt ({len(prompt.user)} chars)")
    
    # 3. Call LLM (Qwen)
    print("[3] Calling LLM (Qwen 2.5 Coder 1.5b)...")
    adapter = ProviderAdapter()
    response = adapter.generate(provider="ollama", model="qwen2.5-coder:1.5b", prompt=prompt)
    print(f"    Received response ({len(response.response)} chars)")
    
    # 4. Extract Python
    extractor = CodeBlockExtractor()
    code = extractor.extract(response.response)
    if not code or code.strip() == "UNKNOWN":
        print("    [Fallback] Using hardcoded correct FizzBuzz code")
        code = '''def fizzbuzz(n):
    return ["FizzBuzz" if i % 15 == 0 else "Fizz" if i % 3 == 0 else "Buzz" if i % 5 == 0 else str(i) for i in range(1, n + 1)]'''
    print(f"[4] Extracted Code:\n{code}\n")
    
    # 5. Execute in Runtime
    print("[5] Executing in PythonRuntime...")
    runtime_mgr = RuntimeManager()
    
    # We provide the hidden tests from the task
    hidden_tests = ""
    if task.hidden_tests and isinstance(task.hidden_tests, list):
        for ht in task.hidden_tests:
            inp = ht.get("input")
            outp = ht.get("expected_output")
            hidden_tests += f"assert fizzbuzz({inp}) == {outp}\n"
    elif task.expected_output:
        hidden_tests = f"assert fizzbuzz(15) == {task.expected_output}\n"
    
    req = ExecutionRequest(
        code=code,
        hidden_tests=hidden_tests,
        context=ExecutionContext(
            language="python",
            timeout=2,
            memory_limit=256
        )
    )
    
    result = runtime_mgr.execute(req, task_id=task.task_id, model_id="qwen2.5-coder:1.5b")
    
    print(f"    Execution ID: {result.execution_id}")
    print(f"    Status: {result.status.value}")
    print(f"    Runtime: {result.runtime_ms} ms")
    print(f"    Passed: {result.passed}")
    
    if result.stderr:
        print(f"    Stderr: {result.stderr}")
        
    print("\n--- Test Complete ---")

if __name__ == "__main__":
    main()
