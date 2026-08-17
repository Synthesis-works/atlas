import sys

file_path = 'packages/database/alembic/versions/f20ab7bfab93_add_missing_evaluation_strategy_id_and_.py'
with open(file_path) as f:
    content = f.read()

target = "    with op.batch_alter_table('datasets', schema=None) as batch_op:\n        batch_op.add_column(sa.Column('org_id', sa.UUID(), nullable=True))"
replacement = "    from sqlalchemy.dialects import postgresql\n    postgresql.ENUM('ACTIVE', 'ARCHIVED', name='dataset_status').create(op.get_bind())\n    with op.batch_alter_table('datasets', schema=None) as batch_op:\n        batch_op.add_column(sa.Column('org_id', sa.UUID(), nullable=True))"

content = content.replace(target, replacement)

with open(file_path, 'w') as f:
    f.write(content)
