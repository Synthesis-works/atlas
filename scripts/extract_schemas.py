import re

file_375 = 'packages/database/alembic/versions/375aa9bc04ec_add_evaluation_schema.py'

with open(file_375, 'r') as f:
    content_375 = f.read()

def extract_table(content, table_name):
    # Match op.create_table( followed by the table name and string literal until the end of the statement.
    match = re.search(r'op\.create_table\(\s*[\'\"]' + table_name + r'[\'\"](.*?)\n\s*def ', content, re.DOTALL)
    if match:
        return match.group(0)[:500]
    return 'NOT FOUND'

tables = ['judges', 'evaluation_results', 'evaluation_artifacts', 'capability_profiles', 'capability_scores']

for t in tables:
    print(f'\\n--- {t} ---')
    print(extract_table(content_375, t))
