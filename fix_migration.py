import sys
import re

file_path = 'packages/database/alembic/versions/f20ab7bfab93_add_missing_evaluation_strategy_id_and_.py'
with open(file_path) as f:
    lines = f.readlines()

tables_to_drop = []
new_lines = []
for line in lines:
    if line.strip().startswith('op.drop_table'):
        tables_to_drop.append(line)
    else:
        new_lines.append(line)

# find where def downgrade is
for i, line in enumerate(new_lines):
    if line.startswith('def downgrade()'):
        for table in tables_to_drop:
            new_lines.insert(i, table)
        break

with open(file_path, 'w') as f:
    f.writelines(new_lines)
