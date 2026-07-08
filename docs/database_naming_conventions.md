# Atlas Database Naming Conventions

To maintain consistency, clarity, and prevent naming collisions across the PostgreSQL database, Project Atlas strictly enforces the following naming conventions.

## 1. Tables
- **Format**: Plural, snake_case.
- **Example**: `users`, `evaluation_strategies`, `model_outputs`.
- **Reasoning**: Pluralization clarifies that the table represents a collection of entities.

## 2. Columns
- **Format**: Singular, snake_case.
- **Example**: `id`, `created_at`, `version_number`.
- **Foreign Keys**: Must end with `_id` (e.g., `project_id`).

## 3. Indexes
- **Format**: `ix_<table_name>_<column_name>_[<column_name_2>]`
- **Example**: `ix_users_email`, `ix_audit_logs_entity`.
- **Reasoning**: Makes it easy to identify which table and columns an index belongs to. SQLAlchemy generally handles this automatically if `index=True` is passed.

## 4. Foreign Keys
- **Format**: `fk_<table_name>_<column_name>_<referred_table_name>`
- **Example**: `fk_users_org_id_organizations`.
- **Reasoning**: Ensures uniqueness globally across the schema, avoiding PostgreSQL's generic `table_column_fkey` collisions.

## 5. Unique Constraints
- **Format**: `uq_<table_name>_<column_name>_[<column_name_2>]`
- **Example**: `uq_users_email`.

## 6. Check Constraints
- **Format**: `chk_<table_name>_<description>`
- **Example**: `chk_configuration_scope`.

## 7. Enums
- **Format**: Singular, snake_case.
- **Example**: `benchmark_state`, `run_status`.
- **Note**: Always map explicitly in SQLAlchemy `ENUM(MyEnum, name="run_status")`.

## SQLAlchemy Naming Convention Configuration
This configuration should be applied to the `Base.metadata` in SQLAlchemy to ensure automated compliance during Alembic migrations:

```python
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "chk_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

Base.metadata = MetaData(naming_convention=convention)
```
