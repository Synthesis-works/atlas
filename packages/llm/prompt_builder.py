import os

from packages.benchmark.models.task import Task

from .models.prompt import Prompt
from .prompt_genealogy import PromptGenealogy


class PromptBuilder:
    """Builds LLM prompts from Benchmark Tasks."""

    @staticmethod
    def build_from_task(task: Task, version: str = "v1", benchmark_pack: str = None) -> Prompt:  # type: ignore
        """
        Converts a Task into a structured Prompt.
        """
        if benchmark_pack:
            prompt_path = os.path.join("D:\\atlas", "prompts", benchmark_pack, f"{version}.md")
        else:
            prompt_path = os.path.join("D:\\atlas", "prompts", f"{version}.md")

        if not os.path.exists(prompt_path):
            raise FileNotFoundError(f"Prompt template {version}.md not found at {prompt_path}")

        with open(prompt_path, encoding="utf-8") as f:
            system = f.read().strip()

        user = f"Task ID:\n{task.task_id}\n\n"
        user += f"Problem:\n{task.description}\n\n"
        user += f"Input:\n{task.input}"

        genealogy = PromptGenealogy(
            os.path.join("D:\\atlas", "prompts"), benchmark_pack=benchmark_pack
        )
        genealogy_info = genealogy.get_prompt_info(version)

        return Prompt(
            system=system,
            user=user,
            metadata={
                "task_id": task.task_id,
                "title": task.title,
                "prompt_version": version,
                "prompt_family": genealogy_info.get("family"),
                "prompt_changes": genealogy_info.get("changes"),
            },
        )
