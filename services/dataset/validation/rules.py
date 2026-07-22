import abc
import csv
import io


class ValidationResult:
    def __init__(self, is_valid: bool, errors: list[str] = None):
        self.is_valid = is_valid
        self.errors = errors or []


class ValidationRule(abc.ABC):
    @abc.abstractmethod
    def validate(self, file_content: bytes) -> ValidationResult:
        pass


class RequiredColumnsRule(ValidationRule):
    def __init__(self, required_columns: list[str]):
        self.required_columns = required_columns

    def validate(self, file_content: bytes) -> ValidationResult:
        try:
            # Assumes CSV for this specific rule example
            content_str = file_content.decode("utf-8")
            reader = csv.reader(io.StringIO(content_str))
            header = next(reader, [])
            missing = [col for col in self.required_columns if col not in header]
            if missing:
                return ValidationResult(False, [f"Missing required columns: {missing}"])
            return ValidationResult(True)
        except Exception as e:
            return ValidationResult(False, [f"Failed to parse CSV header: {str(e)}"])


class UTF8EncodingRule(ValidationRule):
    def validate(self, file_content: bytes) -> ValidationResult:
        try:
            file_content.decode("utf-8")
            return ValidationResult(True)
        except UnicodeDecodeError:
            return ValidationResult(False, ["File is not valid UTF-8 encoded"])
