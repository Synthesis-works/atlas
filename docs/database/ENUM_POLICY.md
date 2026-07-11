# Database ENUM Policy

Project Atlas uses native PostgreSQL `ENUM` types for type safety and performance. However, Alembic (our migration tool) does not natively support autogenerating migrations for adding or modifying Enum values. 

This document outlines the standard operating procedure for safely evolving ENUMs in the database.

## Adding a New Enum Value

When adding a new value to an existing Enum (e.g., adding `TIMEOUT` to `RunStatus`), you **must** write a custom Alembic migration.

1. **Generate an empty migration:**
   ```bash
   alembic revision -m "add_timeout_to_run_status"
   ```

2. **Modify the migration script to use `ALTER TYPE`:**
   ```python
   from alembic import op

   # Define the ENUM name and the new value
   enum_name = 'run_status'
   new_value = 'TIMEOUT'

   def upgrade() -> None:
       # Safe addition in PostgreSQL (Cannot be executed inside a transaction block in older PG versions, 
       # but safe via op.execute in modern versions if isolation level is set)
       with op.get_context().autocommit_block():
           op.execute(f"ALTER TYPE {enum_name} ADD VALUE '{new_value}'")

   def downgrade() -> None:
       # PostgreSQL does NOT support dropping an ENUM value easily.
       # Downgrading an ENUM addition requires a complex multi-step process:
       # 1. Rename existing enum
       # 2. Create new enum without the value
       # 3. Alter tables to use the new enum
       # 4. Drop the old enum
       # For most cases in Atlas, we treat Enum additions as IRREVERSIBLE.
       pass
   ```

## Best Practices
* **Avoid removing Enum values:** Because it requires a massive table rewrite in PostgreSQL, we strongly discourage removing Enum values. If an Enum value is deprecated, handle it at the application layer.
* **Avoid renaming Enum values:** Similarly, renaming is expensive. 
* **State Machines vs. ENUMs:** If you anticipate an Enum will change constantly (e.g., daily), consider whether a foreign-key lookup table or a `String` column with an application-level constraint is more appropriate than a native database ENUM. Native ENUMs should be reserved for relatively stable categories (like `AdapterType` or `RunStatus`).
