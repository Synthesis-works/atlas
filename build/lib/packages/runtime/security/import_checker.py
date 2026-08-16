import ast

from .base import BaseChecker


class ImportChecker(BaseChecker):
    BANNED_MODULES = {"os", "sys", "subprocess", "socket", "shutil", "urllib", "requests", "http"}

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            base_module = alias.name.split(".")[0]
            if base_module in self.BANNED_MODULES:
                self.report_violation(
                    f"Import of banned module '{base_module}' is not allowed.", node
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            base_module = node.module.split(".")[0]
            if base_module in self.BANNED_MODULES:
                self.report_violation(
                    f"Import from banned module '{base_module}' is not allowed.", node
                )
        self.generic_visit(node)
