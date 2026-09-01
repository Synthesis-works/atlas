"""Atlas shared packages (namespace -> regular package).

A single top-level ``packages`` aggregation of Atlas libraries (``packages.llm``,
``packages.database``, etc.).  This ``__init__.py`` makes ``packages`` a regular
package so it is importable from any process that has ``D:/atlas/packages`` on
``sys.path`` (see the ``atlas_packages.pth`` site file).  It deliberately defines
no symbols; individual subpackages carry the actual code.
"""

__version__ = "0.1.0"
