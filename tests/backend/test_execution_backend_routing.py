"""Kill-switch and backend routing behavior of run_execution_task."""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from apps.backend.worker import tasks


@pytest.fixture()
def execution_id_str():
    return str(uuid.uuid4())


def _task_self(retries=0, max_retries=3):
    self_mock = MagicMock()
    self_mock.request.retries = retries
    self_mock.max_retries = max_retries
    return self_mock


class TestKillSwitch:
    def test_disabled_backend_never_executes_or_dispatches(self, execution_id_str):
        with (
            patch.object(tasks.settings, "execution_backend", "disabled"),
            patch.object(tasks, "SessionLocal") as session_cls,
            patch("apps.backend.worker.executor_init.get_executor_for_environment") as get_exec,
        ):
            tasks.run_execution_task(execution_id_str)
            session_cls.assert_not_called()
            get_exec.assert_not_called()

    def test_github_backend_skips_local_docker_path(self, execution_id_str):
        with (
            patch.object(tasks.settings, "execution_backend", "github_actions"),
            patch.object(
                tasks,
                "_dispatch_to_github_with_retry_policy",
            ) as dispatch_mock,
            patch("apps.backend.worker.tasks.SessionLocal") as session_cls,
        ):
            tasks.run_execution_task(execution_id_str)
            dispatch_mock.assert_called_once()

    def test_invalid_backend_name_is_config_error(self):
        from apps.backend.config import Settings

        with pytest.raises(ValueError, match="EXECUTION_BACKEND"):
            Settings(environment="development", execution_backend="lambda")

    def test_github_backend_without_token_is_config_error(self):
        from apps.backend.config import Settings

        with pytest.raises(ValueError, match="GITHUB_EXECUTION_TOKEN"):
            Settings(
                environment="development",
                execution_backend="github_actions",
                github_execution_token=None,
            )
