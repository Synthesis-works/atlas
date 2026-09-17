"""Tests for the hosted agent-session client methods.

The sessions router returns bare dicts (no ``APIResponse`` envelope), so these
tests exercise the ``_get_raw`` / ``_post_raw`` / ``_delete_raw`` paths with
pytest-httpx.
"""

from __future__ import annotations

import pytest

from atlas_sdk.client import AtlasClient
from atlas_sdk.errors import (
    ApiError,
    AuthError,
    ConflictError,
    NotFoundError,
)

SESSION_ID = "11111111-1111-4111-8111-111111111111"


def _session(*, state: str = "AWAITING_APPROVAL") -> dict:
    return {
        "session_id": SESSION_ID,
        "title": "my session",
        "status": "ACTIVE",
        "state": state,
        "provider": "mock",
        "project_id": None,
        "current_task_id": "22222222-2222-4222-8222-222222222222",
        "pending_action": (
            {
                "action": "approve",
                "task_id": "22222222-2222-4222-8222-222222222222",
                "tool_name": "create_benchmark",
                "approval_token_required": True,
            }
            if state == "AWAITING_APPROVAL"
            else None
        ),
        "transcript": [
            {
                "role": "user",
                "content": "hello",
                "task_id": None,
                "created_at": "2026-01-01T00:00:00Z",
            }
        ],
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "last_activity_at": "2026-01-01T00:00:00Z",
    }


def _turn() -> dict:
    return {"session": _session(), "reply": "Tool 'create_benchmark' requires your approval."}


class TestCreateAgentSession:
    def test_create_returns_session(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="POST",
            url="http://localhost:8000/api/v1/agent/sessions",
            json=_session(),
        )
        client = AtlasClient("http://localhost:8000")
        session = client.create_agent_session("Summarize the backlog", provider="mock")
        assert session.session_id == SESSION_ID
        assert session.state == "AWAITING_APPROVAL"
        assert session.pending_action is not None
        assert session.pending_action.action == "approve"
        assert session.transcript[0].role == "user"
        client.close()

    def test_create_sends_body(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="POST",
            url="http://localhost:8000/api/v1/agent/sessions",
            json=_session(),
        )
        client = AtlasClient("http://localhost:8000")
        client.create_agent_session(
            "goal",
            provider="gemini",
            title="T",
            model="gemini-2.5-flash",
            project_id="33333333-3333-4333-8333-333333333333",
        )
        request = httpx_mock.get_request()
        assert request is not None
        body = request.read().decode()
        import json

        assert json.loads(body) == {
            "goal": "goal",
            "provider": "gemini",
            "title": "T",
            "model": "gemini-2.5-flash",
            "project_id": "33333333-3333-4333-8333-333333333333",
        }
        client.close()

    def test_create_requires_auth(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="POST",
            url="http://localhost:8000/api/v1/agent/sessions",
            status_code=401,
            json={"error": {"code": "UNAUTHORIZED", "message": "missing token"}},
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(AuthError):
            client.create_agent_session("goal")
        client.close()


class TestListAgentSessions:
    def test_list_returns_sessions(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:8000/api/v1/agent/sessions",
            json=[_session(state="READY"), _session()],
        )
        client = AtlasClient("http://localhost:8000")
        sessions = client.list_agent_sessions()
        assert len(sessions) == 2
        assert sessions[0].state == "READY"
        assert sessions[1].state == "AWAITING_APPROVAL"
        client.close()


class TestGetAgentSession:
    def test_get_returns_session(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url=f"http://localhost:8000/api/v1/agent/sessions/{SESSION_ID}",
            json=_session(),
        )
        client = AtlasClient("http://localhost:8000")
        session = client.get_agent_session(SESSION_ID)
        assert session.session_id == SESSION_ID
        client.close()

    def test_get_unknown_raises_not_found(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url=f"http://localhost:8000/api/v1/agent/sessions/{SESSION_ID}",
            status_code=404,
            json={"error": {"code": "NOT_FOUND", "message": "not found"}},
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(NotFoundError):
            client.get_agent_session(SESSION_ID)
        client.close()


class TestDeleteAgentSession:
    def test_delete_ok(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="DELETE",
            url=f"http://localhost:8000/api/v1/agent/sessions/{SESSION_ID}",
            json={"status": "success"},
        )
        client = AtlasClient("http://localhost:8000")
        assert client.delete_agent_session(SESSION_ID) is None
        client.close()

    def test_delete_cross_user_forbidden(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="DELETE",
            url=f"http://localhost:8000/api/v1/agent/sessions/{SESSION_ID}",
            status_code=403,
            json={"error": {"code": "FORBIDDEN", "message": "not yours"}},
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(ApiError) as exc:
            client.delete_agent_session(SESSION_ID)
        assert exc.value.status == 403
        client.close()


class TestSendMessage:
    def test_message_returns_turn(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="POST",
            url=f"http://localhost:8000/api/v1/agent/sessions/{SESSION_ID}/messages",
            json=_turn(),
        )
        client = AtlasClient("http://localhost:8000")
        turn = client.send_agent_session_message(SESSION_ID, "hello again")
        assert turn.reply
        assert turn.session.session_id == SESSION_ID
        client.close()

    def test_message_while_busy_raises_conflict(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="POST",
            url=f"http://localhost:8000/api/v1/agent/sessions/{SESSION_ID}/messages",
            status_code=409,
            json={"error": {"code": "HTTP_409", "message": "busy"}},
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(ConflictError):
            client.send_agent_session_message(SESSION_ID, "interrupt")
        client.close()


class TestApprove:
    def test_approve_returns_turn(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="POST",
            url=f"http://localhost:8000/api/v1/agent/sessions/{SESSION_ID}/approve",
            json=_turn(),
        )
        client = AtlasClient("http://localhost:8000")
        turn = client.approve_agent_session(SESSION_ID, approval_token="approval_abcd1234")
        assert turn.session.state == "AWAITING_APPROVAL"
        client.close()

    def test_approve_wrong_token_raises_auth(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="POST",
            url=f"http://localhost:8000/api/v1/agent/sessions/{SESSION_ID}/approve",
            status_code=401,
            json={"error": {"code": "UNAUTHORIZED", "message": "Invalid approval token."}},
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(AuthError):
            client.approve_agent_session(SESSION_ID, approval_token="wrong")
        client.close()


class TestClarify:
    def test_clarify_returns_turn(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="POST",
            url=f"http://localhost:8000/api/v1/agent/sessions/{SESSION_ID}/clarify",
            json=_turn(),
        )
        client = AtlasClient("http://localhost:8000")
        turn = client.clarify_agent_session(SESSION_ID, answer="addition")
        assert turn.reply
        client.close()

    def test_clarify_sends_answer_body(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="POST",
            url=f"http://localhost:8000/api/v1/agent/sessions/{SESSION_ID}/clarify",
            json=_turn(),
        )
        client = AtlasClient("http://localhost:8000")
        client.clarify_agent_session(
            SESSION_ID, answer="subtraction", clarification_id="clarify_ab12"
        )
        request = httpx_mock.get_request()
        assert request is not None
        import json

        assert json.loads(request.read().decode()) == {
            "answer": "subtraction",
            "clarification_id": "clarify_ab12",
        }
        client.close()


class TestCancel:
    def test_cancel_returns_turn(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="POST",
            url=f"http://localhost:8000/api/v1/agent/sessions/{SESSION_ID}/cancel",
            json={"session": _session(state="READY"), "reply": "Task cancelled."},
        )
        client = AtlasClient("http://localhost:8000")
        turn = client.cancel_agent_session(SESSION_ID)
        assert turn.session.state == "READY"
        assert "cancelled" in turn.reply.lower()
        client.close()
