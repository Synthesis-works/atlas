from packages.benchmark.models.task import Task
from .models.prompt import Prompt

class PromptBuilder:
    """Builds LLM prompts from Benchmark Tasks."""
    
    @staticmethod
    def build_from_task(task: Task) -> Prompt:
        """
        Converts a Task into a structured Prompt.
        """
        system = (
            "You are participating in an automated benchmark.\n"
            "Your response will be parsed automatically.\n"
            "Failure to follow the output format will result in automatic failure.\n"
            "Return ONLY the requested output.\n"
            "No markdown.\n"
            "No explanations.\n"
            "No code fences.\n"
            "No labels.\n"
            "No additional text.\n"
            "If unable to answer, output exactly:\nUNKNOWN"
        )
        
        user = f"Task ID:\n{task.task_id}\n\n"
        user += f"Problem:\n{task.description}\n\n"
        user += f"Input:\n{task.input}"
        
        return Prompt(
            system=system,
            user=user,
            metadata={
                "task_id": task.task_id,
                "title": task.title
            }
        )
