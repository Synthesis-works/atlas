import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from atlas_db.core.base import Base, BaseMixin

class Task(Base, BaseMixin):
    __tablename__ = "tasks"

    benchmark_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("benchmark_versions.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    prompts: Mapped[list["Prompt"]] = relationship("Prompt", back_populates="task")
    test_cases: Mapped[list["TestCase"]] = relationship("TestCase", back_populates="task")
    constraints: Mapped[list["Constraint"]] = relationship("Constraint", back_populates="task")
    evaluation_rules: Mapped[list["EvaluationRule"]] = relationship("EvaluationRule", back_populates="task")

class Prompt(Base, BaseMixin):
    __tablename__ = "prompts"

    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    template: Mapped[str] = mapped_column(String, nullable=False)
    system_instruction: Mapped[str | None] = mapped_column(String, nullable=True)

    task: Mapped["Task"] = relationship("Task", back_populates="prompts")

class TestCase(Base, BaseMixin):
    __tablename__ = "test_cases"

    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    input_data: Mapped[str] = mapped_column(String, nullable=False)
    expected_output: Mapped[str] = mapped_column(String, nullable=False)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    task: Mapped["Task"] = relationship("Task", back_populates="test_cases")

class Constraint(Base, BaseMixin):
    __tablename__ = "constraints"

    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[str] = mapped_column(String, nullable=False)

    task: Mapped["Task"] = relationship("Task", back_populates="constraints")

class EvaluationRule(Base, BaseMixin):
    __tablename__ = "evaluation_rules"

    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    rule_definition: Mapped[str] = mapped_column(String, nullable=False)

    task: Mapped["Task"] = relationship("Task", back_populates="evaluation_rules")
