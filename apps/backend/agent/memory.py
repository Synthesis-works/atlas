import logging
from typing import Any, Dict, List, Optional
import httpx

from packages.embedding.base import BaseEmbeddingProvider
from packages.embedding.ollama import OllamaEmbeddingProvider
from packages.embedding.vector import cosine_similarity
from apps.backend.agent.state import AgentTask, ObservationRecord, ToolCallRecord

logger = logging.getLogger(__name__)


class SemanticMemoryItem:
    def __init__(
        self,
        memory_id: str,
        memory_type: str,
        text: str,
        embedding: list[float],
        metadata: dict[str, Any],
    ):
        self.memory_id = memory_id
        self.memory_type = memory_type
        self.text = text
        self.embedding = embedding
        self.metadata = metadata


class SemanticMemoryStore:
    """
    Optional semantic memory store leveraging local Ollama embeddings (Nomic).
    Includes health checking, dynamic model name resolution, and graceful fallback.
    """

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.provider: Optional[BaseEmbeddingProvider] = None
        self.is_available = False
        self.store: list[SemanticMemoryItem] = []
        self._initialize_provider()

    def _initialize_provider(self) -> None:
        try:
            with httpx.Client(timeout=2.0) as client:
                res = client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    models_data = res.json().get("models", [])
                    installed_names = [m.get("name", "") for m in models_data]

                    # Detect nomic or embedding model
                    target_model = None
                    for name in installed_names:
                        if "nomic" in name.lower() or "embed" in name.lower():
                            target_model = name
                            break
                    if not target_model and installed_names:
                        target_model = installed_names[0]

                    if target_model:
                        self.provider = OllamaEmbeddingProvider(
                            model=target_model, base_url=self.base_url
                        )
                        self.is_available = True
                        logger.info(
                            f"SemanticMemoryStore initialized with Ollama model: '{target_model}'"
                        )
                    else:
                        logger.warning("No embedding models found in local Ollama instance.")
        except Exception as e:
            logger.info(f"Semantic memory (Ollama) offline: {e}. Graceful fallback active.")
            self.is_available = False

    def add_memory(
        self, memory_id: str, memory_type: str, text: str, metadata: dict[str, Any]
    ) -> bool:
        if not self.is_available or not self.provider:
            return False
        try:
            emb = self.provider.embed(text)
            self.store.append(SemanticMemoryItem(memory_id, memory_type, text, emb, metadata))
            return True
        except Exception as e:
            logger.warning(f"Failed to add semantic memory item: {e}")
            return False

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        if not self.is_available or not self.provider or not self.store:
            return []
        try:
            q_emb = self.provider.embed(query)
            scored = []
            for item in self.store:
                sim = cosine_similarity(q_emb, item.embedding)
                scored.append((sim, item))

            scored.sort(key=lambda x: x[0], reverse=True)
            results = []
            for sim, item in scored[:limit]:
                results.append(
                    {
                        "memory_id": item.memory_id,
                        "type": item.memory_type,
                        "text": item.text,
                        "relevance": round(sim, 4),
                        "metadata": item.metadata,
                    }
                )
            return results
        except Exception as e:
            logger.warning(f"Semantic search query failed: {e}")
            return []


class AgentMemoryManager:
    """
    Manages short-term and working memory for an active AgentTask.
    Provides structured prompt context without relying on vector embeddings for core DB state.
    """

    def __init__(self, semantic_store: Optional[SemanticMemoryStore] = None):
        self.semantic_store = semantic_store or SemanticMemoryStore()

    def build_prompt_context(self, task: AgentTask) -> str:
        """
        Builds clear, structured text context for the reasoning engine (Gemini).
        """
        lines = []
        lines.append(f"Task Goal: {task.goal}")
        lines.append(f"Status: {task.status.value}")
        lines.append(f"Current Step Index: {task.step_count}")

        # Explicit Task Resource Context (Prevents redundant search calls)
        lines.append("\nCreated Task Resources State:")
        if task.benchmark_id:
            lines.append(
                f"  - BENCHMARK CREATED: benchmark_id='{task.benchmark_id}', benchmark_version_id='{task.benchmark_version_id}'. (DO NOT call search_benchmarks or create_benchmark again)."
            )
        else:
            lines.append("  - BENCHMARK: Not created yet.")

        if task.dataset_id:
            lines.append(
                f"  - DATASET CREATED: dataset_id='{task.dataset_id}'. (DO NOT call create_dataset again; call create_evaluation_case next)."
            )
        else:
            lines.append("  - DATASET: Not created yet.")

        from apps.backend.agent.tools.evaluation_tools import _evaluation_case_store

        eval_cases = _evaluation_case_store.get(task.dataset_id or "", [])
        if eval_cases:
            lines.append(
                f"  - EVALUATION CASES CREATED: {len(eval_cases)} evaluation cases defined (DO NOT call create_evaluation_case again; call validate_benchmark_dataset next)."
            )
        else:
            lines.append("  - EVALUATION CASES: Not created yet.")

        if task.execution_ids:
            lines.append(
                f"  - EXECUTIONS COMPLETED: execution_ids={task.execution_ids}. (DO NOT call run_benchmark or get_run_status again; call evaluate_run)."
            )

        if task.report_id:
            lines.append(
                f"  - REPORT PUBLISHED: report_id='{task.report_id}'. Task workflow complete."
            )

        if task.plan:
            lines.append("\nCurrent Plan:")
            for p in task.plan:
                lines.append(f"  [{p.step_number}] ({p.status}) {p.description}")
                if p.result_summary:
                    lines.append(f"      Result: {p.result_summary}")

        if task.tool_calls:
            lines.append("\nRecent Tool Execution History:")
            for call in task.tool_calls[-6:]:
                matching_obs = next(
                    (
                        obs
                        for obs in task.observations
                        if (
                            getattr(obs, "call_id", None)
                            if not isinstance(obs, dict)
                            else obs.get("call_id")
                        )
                        == call.call_id
                    ),
                    None,
                )
                if matching_obs:
                    succ = getattr(
                        matching_obs,
                        "success",
                        matching_obs.get("success") if isinstance(matching_obs, dict) else False,
                    )
                    out = getattr(
                        matching_obs,
                        "output",
                        matching_obs.get("output") if isinstance(matching_obs, dict) else None,
                    )
                    err = getattr(
                        matching_obs,
                        "error",
                        matching_obs.get("error") if isinstance(matching_obs, dict) else None,
                    )
                    obs_str = f"Success: {succ} | Output: {out}"
                    if err:
                        obs_str += f" | Error: {err}"
                else:
                    obs_str = "Pending"
                lines.append(f"  - Tool '{call.tool_name}' args={call.arguments} -> {obs_str}")

        if task.repair_attempts > 0:
            lines.append(f"\nActive Repair Attempts Count: {task.repair_attempts}")

        if hasattr(task, "past_clarifications") and task.past_clarifications:
            lines.append("\nClarification History:")
            for item in task.past_clarifications:
                lines.append(f"  - Question: {item.get('question')}")
                lines.append(f"    Answer: {item.get('answer')}")

        return "\n".join(lines)
