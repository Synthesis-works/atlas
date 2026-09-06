"""Client-side agent tool layer (Phase 2).

Tools expose Atlas capabilities through the existing ``AtlasClient`` and return
compact, bounded observations for the agent loop.  Read vs write is explicit via
``AgentPermission`` for REPL confirmation gating.
"""
