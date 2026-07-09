from enum import Enum

class TaskState(str, Enum):
    IMPORTED = "imported"
    VALIDATED = "validated"
    READY = "ready"
    PROMPTED = "prompted"
    GENERATED = "generated"
    EXECUTING = "executing"
    EXECUTED = "executed"
    EVALUATED = "evaluated"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskStatus(str, Enum):
    DRAFT = "draft"
    VALIDATED = "validated"
    PUBLISHED = "published"
    ARCHIVED = "archived"

class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HIGH = "high"
    EXPERT = "expert"

class BenchmarkCategory(str, Enum):
    CODING = "coding"
    REASONING = "reasoning"
    MATHEMATICS = "mathematics"
    PLANNING = "planning"
    TOOL_USE = "tool_use"
    KNOWLEDGE = "knowledge"
    SAFETY = "safety"
    LANGUAGE = "language"
    VISION = "vision"
    MULTIMODAL = "multimodal"
    AGENTIC = "agentic"

class Language(str, Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    CPP = "cpp"
    RUST = "rust"
    GO = "go"
    ENGLISH = "english"
    OTHER = "other"

class ExecutionMode(str, Enum):
    LOCAL = "local"
    DOCKER = "docker"
    REMOTE = "remote"

class LicenseType(str, Enum):
    MIT = "MIT"
    APACHE_2_0 = "Apache-2.0"
    GPL_3_0 = "GPL-3.0"
    CC_BY_4_0 = "CC-BY-4.0"
    PROPRIETARY = "proprietary"
    OTHER = "other"

class Visibility(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    INTERNAL = "internal"

class BenchmarkType(str, Enum):
    STANDARD = "standard"
    ADAPTIVE = "adaptive"
    SYNTHETIC = "synthetic"

class EvaluationStrategy(str, Enum):
    HIDDEN_TESTS = "hidden_tests"
    EXACT_MATCH = "exact_match"
    RULE_BASED = "rule_based"
    METRIC_BASED = "metric_based"
    LLM_JUDGE = "llm_judge"
    HUMAN_JUDGE = "human_judge"
    HYBRID_JUDGE = "hybrid_judge"
