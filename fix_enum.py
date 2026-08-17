import sys

file_path = 'packages/database/alembic/versions/f20ab7bfab93_add_missing_evaluation_strategy_id_and_.py'
with open(file_path) as f:
    content = f.read()

# Add ENUM create for upgrade
target_upgrade = "    with op.batch_alter_table('dataset_versions', schema=None) as batch_op:\n        batch_op.add_column(sa.Column('lifecycle', postgresql.ENUM('UPLOADED', 'VALIDATING', 'VALID', 'PUBLISHED', 'FAILED', name='dataset_lifecycle'), nullable=False))"
replacement_upgrade = "    from sqlalchemy.dialects import postgresql\n    postgresql.ENUM('UPLOADED', 'VALIDATING', 'VALID', 'PUBLISHED', 'FAILED', name='dataset_lifecycle').create(op.get_bind())\n    with op.batch_alter_table('dataset_versions', schema=None) as batch_op:\n        batch_op.add_column(sa.Column('lifecycle', postgresql.ENUM('UPLOADED', 'VALIDATING', 'VALID', 'PUBLISHED', 'FAILED', name='dataset_lifecycle'), nullable=False))"

# Add ENUM drop for downgrade
target_downgrade = "    with op.batch_alter_table('dataset_versions', schema=None) as batch_op:\n        batch_op.add_column(sa.Column('validation_status', postgresql.ENUM('PENDING', 'VALIDATED', 'FAILED', name='dataset_validation_status'), autoincrement=False, nullable=True))"
replacement_downgrade = "    with op.batch_alter_table('dataset_versions', schema=None) as batch_op:\n        batch_op.add_column(sa.Column('validation_status', postgresql.ENUM('PENDING', 'VALIDATED', 'FAILED', name='dataset_validation_status'), autoincrement=False, nullable=True))\n\n    postgresql.ENUM('UPLOADED', 'VALIDATING', 'VALID', 'PUBLISHED', 'FAILED', name='dataset_lifecycle').drop(op.get_bind())"

content = content.replace(target_upgrade, replacement_upgrade)
content = content.replace(target_downgrade, replacement_downgrade)

with open(file_path, 'w') as f:
    f.write(content)
