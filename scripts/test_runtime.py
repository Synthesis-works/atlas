import json
import os
from packages.benchmark.manager.facade import BenchmarkManager
from packages.llm.prompt_builder import PromptBuilder
from packages.llm.clients.ollama import OllamaAdapter
from packages.evaluation.extractors.code_block import CodeBlockExtractor
from packages.runtime.models.execution_request import ExecutionRequest, ExecutionContext
from packages.runtime.manager.runtime_manager import RuntimeManager
from packages.evaluation.results.result import EvaluationResult

def main():
    print("--- Atlas Phase 5: Runtime Integration Test ---")
    
    # 1. Load Benchmark
    manager = BenchmarkManager()
    manager.load_benchmarks("benchmarks/coding")
    task = manager.get_task("coding-fizzbuzz-001")
    print(f"[1] Loaded Task: {task.task_id}")
    
    # 2. Build Prompt
    prompt = PromptBuilder.build_few_shot(task)
    print(f"[2] Built Prompt ({len(prompt.content)} chars)")
    
    # 3. Call LLM (Qwen)
    print("[3] Calling LLM (Qwen 2.5 Coder 1.5b)...")
    adapter = OllamaAdapter(model_name="qwen2.5-coder:1.5b")
    response = adapter.generate(prompt)
    print(f"    Received response ({len(response.content)} chars)")
    
    # 4. Extract Python
    extractor = CodeBlockExtractor()
    code = extractor.extract(response.content)
    print(f"[4] Extracted Code:\n{code}\n")
    
    # 5. Execute in Runtime
    print("[5] Executing in PythonRuntime...")
    runtime_mgr = RuntimeManager()
    
    # We provide the hidden tests from the task
    # Our custom fizzbuzz.yaml doesn't have hidden_tests yet, so let's mock one if missing, 
    # but let's check if it has expected_output
    hidden_tests = task.hidden_tests if task.hidden_tests else ""
    if not hidden_tests and task.expected_output:
        hidden_tests = f"assert fizzbuzz(15) == '{task.expected_output}'\nassert fizzbuzz(3) == 'Fizz'\nassert fizzbuzz(5) == 'Buzz'\n"
    
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
