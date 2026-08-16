import ast


class BaseChecker(ast.NodeVisitor):
    def __init__(self):
        self.violations = []

    def report_violation(self, message: str, node: ast.AST):
        line = getattr(node, "lineno", -1)
        self.violations.append(f"Line {line}: {message}")
