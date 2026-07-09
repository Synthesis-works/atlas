import ast
from .base import BaseChecker

class CallChecker(BaseChecker):
    BANNED_CALLS = {"eval", "exec", "compile", "open", "input"}
    BANNED_ATTRIBUTES = {"system", "popen", "run", "rmtree", "remove", "unlink", "mkdir", "makedirs"}

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name):
            if node.func.id in self.BANNED_CALLS:
                self.report_violation(f"Call to banned function '{node.func.id}' is not allowed.", node)
        elif isinstance(node.func, ast.Attribute):
            if node.func.attr in self.BANNED_ATTRIBUTES:
                self.report_violation(f"Call to banned attribute '{node.func.attr}' is not allowed.", node)
        self.generic_visit(node)
