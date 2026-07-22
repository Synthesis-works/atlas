import os
import re


def get_created_tables(file_path):
    with open(file_path) as f:
        content = f.read()
    return re.findall(r"op\.create_table\(\s*['\"]([^'\"]+)['\"]", content)


migrations_dir = "packages/database/alembic/versions"
all_tables = {}

for filename in sorted(os.listdir(migrations_dir)):
    if filename.endswith(".py"):
        tables = get_created_tables(os.path.join(migrations_dir, filename))
        if tables:
            all_tables[filename] = tables

for filename, tables in all_tables.items():
    print(f"{filename}: {tables}")
