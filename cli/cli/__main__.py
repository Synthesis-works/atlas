"""``python -m cli`` fallback entry point.

Windows/MS Store Python installs may not put the ``atlas`` console script on
``PATH``.  This module lets the same CLI be invoked as ``python -m cli`` without
creating a second implementation — it just calls the existing package entry
point (``cli.app.entrypoint``).
"""

from cli.app import entrypoint

if __name__ == "__main__":
    entrypoint()
