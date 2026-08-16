import ast

from ..exceptions import CompilationException, SecurityException
from .call_checker import CallChecker
from .import_checker import ImportChecker


class SecurityValidator:
    def __init__(self):
        self.checkers = [ImportChecker(), CallChecker()]

    def validate(self, source_code: str) -> None:
        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            raise CompilationException(f"Syntax error: {e}")

        all_violations: list[str] = []

        for checker in self.checkers:
            checker.visit(tree)
            all_violations.extend(checker.violations)

        if all_violations:
            violation_msg = "; ".join(all_violations)
            raise SecurityException(f"Security validation failed: {violation_msg}")
