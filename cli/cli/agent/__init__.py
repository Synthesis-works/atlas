"""Client-side Atlas agent package (Gemini-CLI-style terminal).

The agent layer sits on top of the deterministic CLI: its tools call the same
``AtlasClient`` SDK methods the deterministic commands use, and it owns its own
reasoning loop.  This package is gradually filled by later phases (tool layer,
loop, REPL/one-shot).
"""
