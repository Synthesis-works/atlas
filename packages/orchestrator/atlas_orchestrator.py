
from packages.benchmark.manager.facade import BenchmarkManager
from packages.llm.clients.adapter import ProviderAdapter
from packages.runtime.manager.runtime_manager import RuntimeManager

from .models import JobConfig, TaskRunResult, TaskRunState
from .state_manager import StateManager
from .metrics_aggregator import MetricsAggregator

from .pipeline.stages.load_stage import LoadTaskStage
from .pipeline.stages.prompt_stage import PromptStage
from .pipeline.stages.generation_stage import GenerationStage
from .pipeline.stages.extraction_stage import ExtractionStage
from .pipeline.stages.execution_stage import ExecutionStage
from .pipeline.stages.evaluation_stage import EvaluationStage
from .pipeline.stages.persistence_stage import PersistenceStage

from packages.benchmark.registry.memory import InMemoryRegistry
from packages.benchmark.validation.schema import SchemaValidator
from packages.benchmark.validation.metadata import MetadataValidator
from packages.benchmark.validation.registry import RegistryValidator
from packages.benchmark.loader.yaml_loader import YAMLLoader

from .pipeline.stages.repair_stage import RepairStage

class AtlasOrchestrator:
    def __init__(self, base_dir: str = "results/jobs"):
        registry = InMemoryRegistry()
        validators = [SchemaValidator(), MetadataValidator(), RegistryValidator(registry)]
        loaders = {"yaml": YAMLLoader()}
        self.benchmark_mgr = BenchmarkManager(registry, validators, loaders)
        # Note: Datasets are loaded per pack in run_pack()
        self.provider_adapter = ProviderAdapter()
        self.runtime_mgr = RuntimeManager()
        self.state_mgr = StateManager(base_dir=base_dir)
        self.metrics_aggregator = MetricsAggregator()
        
        self.pipeline = [
            LoadTaskStage(),
            PromptStage(),
            GenerationStage(),
            ExtractionStage(),
            ExecutionStage(),
            EvaluationStage(),
            RepairStage(max_retries=1),
            PersistenceStage()
        ]

    # The looping and resume logic is now managed by ExperimentRunner.

    def _run_task(self, job_id: str, task_id: str, config: JobConfig) -> TaskRunResult:
        print(f"  -> Running task {task_id}...")
        
        prompt_version = getattr(config, "prompt_version", "v1")
        
        result = TaskRunResult(
            task_id=task_id,
            model=config.model,
            prompt_version=prompt_version,
            runtime="python"
        )
        context = {
            "job_config": config,
            "benchmark_manager": self.benchmark_mgr,
            "provider_adapter": self.provider_adapter,
            "runtime_manager": self.runtime_mgr,
            "state_manager": self.state_mgr,
            "pack_name": config.benchmark_pack,
            "pack_tasks": self.pack_tasks,
            "needs_reexecution": False
        }
        
        while True:
            context["needs_reexecution"] = False
            for stage in self.pipeline:
                # If we're looping and it's Load/Prompt/Gen, skip them if we already generated repaired code
                if result.state == TaskRunState.GENERATED and stage.__class__.__name__ in ["LoadTaskStage", "PromptStage", "GenerationStage"]:
                    continue
                    
                stage.execute(context, result)
                if result.state == TaskRunState.FAILED and not context.get("needs_reexecution"):
                    # Only break if it's failed AND the repair stage didn't flag a re-execution
                    print(f"     [FAILED] at {stage.__class__.__name__}: {result.error_message}")
                    break
                    
            if not context.get("needs_reexecution"):
                break
                
        if result.state == TaskRunState.FAILED:
            PersistenceStage().execute(context, result)
            
        return result
