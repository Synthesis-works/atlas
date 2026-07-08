from packages.benchmark.models.task import Task
from .models.prompt import Prompt

class PromptBuilder:
    """Builds LLM prompts from Benchmark Tasks."""
    
    @staticmethod
    def build_from_task(task: Task) -> Prompt:
        """
        Converts a Task into a structured Prompt.
        """
        system = "You are participating in an AI benchmark."
        
        user = f"Task ID:\n{task.task_id}\n\n"
        user += f"Problem:\n{task.description}\n\n"
        user += f"Input:\n{task.input}\n\n"
        user += "Return ONLY the answer.\nDo not explain your reasoning."
        
        return Prompt(
            system=system,
            user=user,
            metadata={
                "task_id": task.task_id,
                "title": task.title
            }
        )
