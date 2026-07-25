import glob

for file in glob.glob("packages/database/alembic/versions/*.py"):
    with open(file, encoding="utf-8") as f:
        content = f.read()
    if "sa.text('now()')" in content:
        content = content.replace("sa.text('now()')", "sa.text('CURRENT_TIMESTAMP')")
        with open(file, "w", encoding="utf-8") as f:
            f.write(content)
