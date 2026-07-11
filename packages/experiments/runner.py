import os
import json
import uuid
import datetime
import random
from typing import Dict, Any

from packages.orchestrator.atlas_orchestrator import AtlasOrchestrator
from packages.orchestrator.models import JobConfig
from .models import ExperimentConfig
from packages.llm.prompt_builder import PromptBuilder

class ExperimentRunner:
    def __init__(self, base_dir: str = "results/experiments"):
        self.base_dir = base_dir
        self.orchestrator = AtlasOrchestrator(base_dir=base_dir)
        
    def run(self, exp_config: ExperimentConfig) -> str:
        # Create an exp ID
        exp_id = f"exp-{exp_config.dataset.lower()}-{uuid.uuid4().hex[:6]}"
        print(f"=== Starting Experiment {exp_id} ===")
        print(f"Dataset: {exp_config.dataset}, Model: {exp_config.model}")
        print(f"Prompt Version: {exp_config.prompt_version}, Tasks: {exp_config.max_tasks or 'All'}")
        
        # Load tasks
        tasks = []
        pack_name = exp_config.dataset.lower()
        if pack_name == "humaneval":
            from packages.datasets.importers.humaneval import HumanEvalImporter
            pack = HumanEvalImporter().import_pack()
            tasks = pack.tasks
        elif pack_name == "mbpp":
            from packages.datasets.importers.mbpp import MBPPImporter
            pack = MBPPImporter().import_pack()
            tasks = pack.tasks
        else:
            raise ValueError(f"Unknown dataset: {exp_config.dataset}")
            
        if exp_config.shuffle:
            random.seed(exp_config.seed)
            random.shuffle(tasks)
            
        # We might also want to set random seed globally just in case
        random.seed(exp_config.seed)
            
        if exp_config.max_tasks is not None:
            tasks = tasks[:exp_config.max_tasks]
            
        # We need to inject these tasks into the orchestrator directly, instead of run_pack doing it
        # Let's bypass run_pack and just do the equivalent logic here using the orchestrator's state_manager
        
        job_config = JobConfig(
            job_id=exp_id,
            benchmark_pack=exp_config.dataset,
            model=exp_config.model,
            provider=getattr(exp_config, "provider", "ollama"),
            prompt_version=exp_config.prompt_version,
            seed=exp_config.seed,
            git_commit=exp_config.git_commit,
            python_version=exp_config.python_version,
            ollama_version=exp_config.ollama_version,
            model_digest=exp_config.model_digest,
            os_info=exp_config.os_info,
            cpu_info=exp_config.cpu_info,
            ram_gb=exp_config.ram_gb,
            atlas_version=exp_config.atlas_version,
            parent_experiment=exp_config.parent_experiment,
            lineage_change=exp_config.lineage_change,
            lineage_reason=exp_config.lineage_reason
        )
        
        self.orchestrator.pack_tasks = {t.task_id: t for t in tasks}
        task_ids = [t.task_id for t in tasks]
        
        self.orchestrator.state_mgr.init_job(job_config, task_ids)
        
        # Save ExperimentConfig
        exp_dir = os.path.join(self.base_dir, exp_id)
        with open(os.path.join(exp_dir, "experiment_config.json"), "w") as f:
            f.write(exp_config.model_dump_json(indent=2))
            
        # Save Prompt template (using the first task as sample)
        if len(tasks) > 0:
            sample_prompt = PromptBuilder.build_from_task(tasks[0], version=exp_config.prompt_version, benchmark_pack=exp_config.dataset.lower())
            with open(os.path.join(exp_dir, "prompt.txt"), "w") as f:
                f.write(sample_prompt.user)
                
        # Save Published Reference (placeholder for now)
        published_ref = {
            "atlas": {
                "model": exp_config.model,
                "temperature": exp_config.temperature,
                "samples": 1
            },
            "published_reference": {
                "benchmark": exp_config.dataset,
                "notes": "Published values may use multiple samples, different prompts, or pass@k."
            }
        }
        with open(os.path.join(exp_dir, "published_reference.json"), "w") as f:
            json.dump(published_ref, f, indent=2)
            
        # Run
        pending = self.orchestrator.state_mgr.load_pending_tasks(exp_id)
        self._run_loop(exp_id, pending, job_config, exp_config, len(tasks))
        return exp_id

    def resume(self, exp_id: str) -> None:
        exp_dir = os.path.join(self.base_dir, exp_id)
        exp_config_path = os.path.join(exp_dir, "experiment_config.json")
        if not os.path.exists(exp_config_path):
            print(f"Experiment {exp_id} not found.")
            return

        with open(exp_config_path, "r", encoding="utf-8") as f:
            exp_config = ExperimentConfig(**json.load(f))
            
        # Recreate job config
        job_config = JobConfig(
            job_id=exp_id,
            benchmark_pack=exp_config.dataset,
            model=exp_config.model,
            provider=getattr(exp_config, "provider", "ollama"),
            prompt_version=exp_config.prompt_version,
            seed=exp_config.seed,
            parent_experiment=exp_config.parent_experiment,
            lineage_change=exp_config.lineage_change,
            lineage_reason=exp_config.lineage_reason
        )

        pack_name = exp_config.dataset.lower()
        if pack_name == "humaneval":
            from packages.datasets.importers.humaneval import HumanEvalImporter
            pack = HumanEvalImporter().import_pack()
            self.orchestrator.pack_tasks = {t.task_id: t for t in pack.tasks}
        elif pack_name == "mbpp":
            from packages.datasets.importers.mbpp import MBPPImporter
            pack = MBPPImporter().import_pack()
            self.orchestrator.pack_tasks = {t.task_id: t for t in pack.tasks}
            
        total_tasks = len(self.orchestrator.pack_tasks)
        if exp_config.max_tasks is not None:
            total_tasks = min(total_tasks, exp_config.max_tasks)
            
        pending = self.orchestrator.state_mgr.load_pending_tasks(exp_id)
        self._run_loop(exp_id, pending, job_config, exp_config, total_tasks)
        
    def _run_loop(self, exp_id: str, pending: list, job_config: JobConfig, exp_config: ExperimentConfig, total_tasks: int):
        from packages.orchestrator.progress_ui import ProgressUI
        
        ui = ProgressUI(exp_id, exp_config.dataset, exp_config.model, exp_config.prompt_version, total_tasks)
        
        # Pre-populate UI with existing results (for resume)
        results = self.orchestrator.state_mgr.load_all_results(exp_id)
        for r in results:
            ui.update(r)
        
        if ui.completed > 0:
            ui.render()
            
        try:
            for i, task_id in enumerate(pending, 1):
                self.orchestrator._run_task(exp_id, task_id, job_config)
                
                # Fetch result and update UI
                res_path = os.path.join(self.base_dir, exp_id, "tasks", f"{task_id}.json")
                if os.path.exists(res_path):
                    from packages.orchestrator.models import TaskResult
                    with open(res_path, "r") as f:
                        res_obj = TaskResult(**json.load(f))
                        ui.update(res_obj)
                        ui.render()
                
                # Checkpoint every 25 tasks
                if ui.completed % 25 == 0:
                    self._save_checkpoint(exp_id, ui)
                    
        except KeyboardInterrupt:
            print(f"\n[{exp_id}] Saving checkpoint...")
            self._save_checkpoint(exp_id, ui)
            print("Saving registry...")
            self._finalize_experiment(exp_id, exp_config)
            print("\nExperiment safely paused.")
            print(f"Resume:\n\npy scripts/resume_experiment.py --job {exp_id}\n")
            import sys
            sys.exit(0)
            
        self._save_checkpoint(exp_id, ui)
        self._finalize_experiment(exp_id, exp_config)
        print(f"\n=== Experiment {exp_id} Completed ===")

    def _save_checkpoint(self, exp_id: str, ui):
        checkpoint = {
            "completed": ui.completed,
            "passed": ui.passed,
            "failed": ui.failed,
            "pass_at_1": (ui.passed / ui.completed) if ui.completed > 0 else 0.0,
            "average_latency": (sum(ui.latencies) / len(ui.latencies) / 1000.0) if ui.latencies else 0.0,
            "total_tasks": ui.total_tasks
        }
        with open(os.path.join(self.base_dir, exp_id, "checkpoint.json"), "w") as f:
            json.dump(checkpoint, f, indent=2)

    def _finalize_experiment(self, exp_id: str, exp_config: ExperimentConfig):
        # Generate summary
        results = self.orchestrator.state_mgr.load_all_results(exp_id)
        if not results:
            return
            
        profile = self.orchestrator.metrics_aggregator.aggregate(results)
        
        profile["job_id"] = exp_id
        profile["benchmark_pack"] = exp_config.dataset
        profile["model"] = exp_config.model
        profile["prompt_version"] = exp_config.prompt_version
        
        self.orchestrator.state_mgr.save_profile(exp_id, profile)
        
        # Create summary.json (alias for profile but with extra exp context)
        summary = {
            "experiment_id": exp_id,
            "config": json.loads(exp_config.model_dump_json()),
            "metrics": profile
        }
        with open(os.path.join(self.base_dir, exp_id, "summary.json"), "w") as f:
            json.dump(summary, f, indent=2)
            
        # Register experiment
        from packages.experiments.registry import ExperimentRegistry
        registry = ExperimentRegistry(registry_file=os.path.join(self.base_dir, "registry.json"))
        registry.register(
            exp_id=exp_id,
            config=json.loads(exp_config.model_dump_json()),
            metrics=profile
        )
