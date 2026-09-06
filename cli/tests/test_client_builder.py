"""Tests for ``cli.client.build_client`` — the single shared client path (Slice 5).

Covers plumbing of ``--retries`` into the SDK constructor and behavioral
proof that the value actually changes retry attempts on idempotent GETs
while POST stays non-retried.
"""

from __future__ import annotations

import http
from unittest.mock import patch

import httpx
import pytest
from atlas_sdk.errors import ServerError
from click.testing import CliRunner

from cli.app import main
from cli.client import build_client
from cli.config import AtlasConfig, load_config


class _DeterministicResponseTransport:
    """Fake ``httpx.Client`` returning a scripted sequence of responses.

    Mirrors the call signature used by ``AtlasClient._do_request``.
    """

    def __init__(self, responses: list[httpx.Response]) -> None:
        self._responses = list(responses)
        self.request_count = 0

    def request(
        self,
        method: str,
        url: str,
        *,
        json: object = None,
        params: dict[str, object] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        self.request_count += 1
        response = self._responses.pop(0)
        response.request = httpx.Request(method, url)
        return response

    def close(self) -> None:
        return None


# ── builder plumbing ────────────────────────────────────────────────────


def test_build_client_passes_retries_to_sdk_constructor() -> None:
    for retries in (0, 3, 9):
        with patch("cli.client.AtlasClient") as mock_cls:
            build_client(load_config(retries=retries))
        assert mock_cls.call_args.kwargs["max_retries"] == retries


def test_build_client_default_retries_is_three() -> None:
    with patch("cli.client.AtlasClient") as mock_cls:
        build_client(load_config())
    assert mock_cls.call_args.kwargs["max_retries"] == 3


def test_build_client_forwards_base_url_and_timeout() -> None:
    with patch("cli.client.AtlasClient") as mock_cls:
        build_client(load_config(base_url="http://custom:9000", timeout=30.0))
    assert mock_cls.call_args.args[0] == "http://custom:9000"
    assert mock_cls.call_args.kwargs["timeout"] == 30.0


def test_build_client_timeout_override_wins() -> None:
    with patch("cli.client.AtlasClient") as mock_cls:
        build_client(load_config(timeout=30.0), timeout=5.0)
    assert mock_cls.call_args.kwargs["timeout"] == 5.0


def test_build_client_supplies_static_token_when_configured() -> None:
    with patch("cli.client.AtlasClient") as mock_cls:
        build_client(AtlasConfig(token="secret-token"))
    supplier = mock_cls.call_args.kwargs["token_supplier"]
    assert supplier is not None
    assert supplier() == "secret-token"


def test_build_client_omits_token_supplier_when_anonymous() -> None:
    with patch("cli.client.AtlasClient") as mock_cls:
        build_client(load_config())
    assert mock_cls.call_args.kwargs["token_supplier"] is None


def test_retries_flag_reaches_builder_via_cli(runner: CliRunner) -> None:
    with patch("cli.client.AtlasClient") as mock_cls:
        result = runner.invoke(main, ["--output", "quiet", "--retries", "5", "health"])
    assert result.exit_code == 0
    assert mock_cls.call_args.kwargs["max_retries"] == 5


# ── behavioral proof: --retries drives the real SDK retry loop ──────────


def test_get_retries_according_to_configured_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("time.sleep", lambda _seconds: None)
    transport = _DeterministicResponseTransport(
        [httpx.Response(http.HTTPStatus.SERVICE_UNAVAILABLE), httpx.Response(200, json=[])]
    )
    client = build_client(AtlasConfig(base_url="http://test", retries=1))
    client._http = transport  # type: ignore[attr-defined]

    targets = client.list_dispatch_targets()

    assert targets == []
    assert transport.request_count == 2


def test_get_retries_zero_fails_after_single_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("time.sleep", lambda _seconds: None)
    transport = _DeterministicResponseTransport(
        [httpx.Response(http.HTTPStatus.SERVICE_UNAVAILABLE)]
    )
    client = build_client(AtlasConfig(base_url="http://test", retries=0))
    client._http = transport  # type: ignore[attr-defined]

    with pytest.raises(ServerError):
        client.list_dispatch_targets()

    assert transport.request_count == 1


def test_post_is_never_retried_even_with_high_retry_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("time.sleep", lambda _seconds: None)
    transport = _DeterministicResponseTransport(
        [httpx.Response(http.HTTPStatus.SERVICE_UNAVAILABLE)]
    )
    client = build_client(AtlasConfig(base_url="http://test", retries=5))
    client._http = transport  # type: ignore[attr-defined]

    with pytest.raises(ServerError):
        client.submit_execution(
            "11111111-1111-1111-1111-111111111111",
            target_model="mock",
        )

    assert transport.request_count == 1
