import ast
import numpy as np
from typing import Dict, Any

class DifficultyPredictor:
    """
    Deterministic Stage A difficulty scorer.
    """
    
    @staticmethod
    def get_ast_metrics(code: str) -> tuple:
        """Returns (cyclomatic_complexity, max_depth)"""
        try:
            tree = ast.parse(code)
        except Exception:
            return (1, 1)
            
        # Very basic cyclomatic complexity: count control flow nodes + 1
        complexity = 1
        max_depth = 1
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.For, ast.While, ast.And, ast.Or, ast.ExceptHandler)):
                complexity += 1
                
        def get_depth(node):
            if not hasattr(node, "body") and not hasattr(node, "orelse"):
                return 1
            child_depths = [1]
            if hasattr(node, "body"):
                for child in getattr(node, "body", []):
                    child_depths.append(get_depth(child))
            if hasattr(node, "orelse"):
                for child in getattr(node, "orelse", []):
                    child_depths.append(get_depth(child))
            return 1 + max(child_depths)
            
        max_depth = get_depth(tree)
        return (complexity, max_depth)

    @staticmethod
    def compute_difficulty(task_result: Dict[str, Any], pass_rate: float = 0.5) -> float:
        """
        Computes deterministic difficulty score [0, 1].
        1.0 means extremely difficult.
        """
        code = task_result.get("extracted_code", "")
        if not code:
            code = task_result.get("prompt", "")
            
        complexity, ast_depth = DifficultyPredictor.get_ast_metrics(code)
        
        length_score = min(1.0, len(code) / 1000.0)
        complexity_score = min(1.0, complexity / 10.0)
        depth_score = min(1.0, ast_depth / 5.0)
        
        # pass_rate is globally calculated or historically available
        # Inverse pass rate: lower pass rate = higher difficulty
        failure_rate = 1.0 - pass_rate
        
        # Weighted average
        score = (
            (0.4 * failure_rate) +
            (0.3 * complexity_score) +
            (0.2 * depth_score) +
            (0.1 * length_score)
        )
        
        return min(1.0, max(0.0, score))
