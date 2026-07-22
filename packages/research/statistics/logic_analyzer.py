from typing import Any


class LogicAnalyzer:
    def __init__(self, llm_provider=None):
        self.llm_provider = llm_provider

    def analyze(self, task: dict[str, Any]) -> str:
        """
        Analyzes a failed task (Logic Error) and returns a granular category.
        Uses rule-based heuristics first, then falls back to LLM.
        """
        err_msg = task.get("error_message") or task.get("exception") or ""
        stderr = task.get("stderr") or ""
        combined_err = (err_msg + " " + stderr).lower()

        # 1. Rule-Based Classification
        if "assertionerror" in combined_err:
            return "Wrong Output"
        if "timeout" in combined_err or "time limit" in combined_err:
            return "Infinite Loop / Inefficient Algorithm"
        if "recursionerror" in combined_err or "maximum recursion depth" in combined_err:
            return "Recursion Failure"
        if "indexerror" in combined_err or "list index out of range" in combined_err:
            return "Boundary Error"
        if "keyerror" in combined_err:
            return "Data Structure Error (Missing Key)"
        if "typeerror" in combined_err:
            return "Type Mismatch"
        if "zerodivisionerror" in combined_err or "math domain error" in combined_err:
            return "Math Error"

        # 2. LLM Fallback
        if self.llm_provider:
            # Here we would query the LLM:
            # "Classify this error: {combined_err}. Options: Wrong Algorithm, Off-by-one, Edge Case, etc."
            # Since LLM is an async/external call, we'll simulate or make a synchronous call depending on the provider.
            return self._query_llm(task)

        return "Unknown Logic Error"

    def _query_llm(self, task: dict[str, Any]) -> str:
        # Placeholder for LLM fallback
        # Given this is a 1.5B model, it might be better to just rely on rules or have a strong prompt.
        # For now, if rules fail, we return a generic fallback until we wire up an explicit prompt.
        return "LLM Analysis Required (Unknown)"
