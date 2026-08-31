"""Shared ``AtlasClient`` construction (Slice 5).

Every command builds its HTTP client through :func:`build_client` so global
configuration (``base_url``, ``timeout``, ``retries``, token) is plumbed in
one place.  Retry semantics are the SDK's own: idempotent GET/HEAD requests
may be retried up to ``cfg.retries`` times; POST is never retried.
"""

from __future__ import annotations

from atlas_sdk import AtlasClient, StaticTokenSupplier
from atlas_sdk.auth import TokenSupplier

from cli.config import AtlasConfig


def build_client(
    cfg: AtlasConfig,
    *,
    token_supplier: TokenSupplier | None = None,
    timeout: float | None = None,
) -> AtlasClient:
    """Construct an :class:`AtlasClient` from resolved CLI configuration.

    The token supplier defaults to a static supplier over the configured
    token (``None`` when unauthenticated); an explicit supplier wins.
    ``timeout`` overrides ``cfg.timeout`` when provided (used by ``run
    watch``, which polls with a short per-request timeout).
    """
    supplier = token_supplier
    if supplier is None and cfg.token:
        supplier = StaticTokenSupplier(cfg.token)
    return AtlasClient(
        cfg.base_url,
        token_supplier=supplier,
        timeout=timeout if timeout is not None else cfg.timeout,
        max_retries=cfg.retries,
    )
