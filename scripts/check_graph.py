import os
import re

versions_dir = "packages/database/alembic/versions"
for filename in os.listdir(versions_dir):
    if not filename.endswith(".py"):
        continue
    filepath = os.path.join(versions_dir, filename)
    with open(filepath) as f:
        content = f.read()

    rev_match = re.search(r"revision(?:.*?)=\s*['\"](.*?)['\"]", content)
    down_rev_match = re.search(r"down_revision(?:.*?)=\s*(None|['\"](.*?)['\"]|\((.*?)\))", content)

    revision = rev_match.group(1) if rev_match else "UNKNOWN"

    if down_rev_match:
        if down_rev_match.group(1) == "None":
            down_revision = "None"
        elif down_rev_match.group(2):
            down_revision = down_rev_match.group(2)
        elif down_rev_match.group(3):
            # Parse tuple
            down_revision = str([x.strip(" '\":") for x in down_rev_match.group(3).split(",")])
        else:
            down_revision = "UNKNOWN"
    else:
        down_revision = "UNKNOWN"

    print(f"File: {filename}")
    print(f"  Revision: {revision}")
    print(f"  Down Revision: {down_revision}")
