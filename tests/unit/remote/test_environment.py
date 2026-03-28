from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from runicorn.remote.environment import RemoteEnvironmentDetector


def _make_connection(timeout: int = 30) -> MagicMock:
    connection = MagicMock()
    connection.config = SimpleNamespace(timeout=timeout)
    connection.env_cache = {}
    return connection


def test_detect_all_environments_extends_conda_timeout():
    connection = _make_connection(timeout=30)

    def exec_command(command: str, timeout: int | None = None):
        if command == "which conda":
            return ("/opt/miniconda3/bin/conda\n", "", 0)
        if command == "/opt/miniconda3/bin/conda info --envs":
            return (
                "# conda environments:\n"
                "base                  *  /opt/miniconda3\n"
                "torch                    /opt/miniconda3/envs/torch\n",
                "",
                0,
            )
        if command == "/opt/miniconda3/bin/python --version":
            return ("Python 3.11.9\n", "", 0)
        if command == "/opt/miniconda3/envs/torch/bin/python --version":
            return ("Python 3.10.14\n", "", 0)
        if command == "which python3":
            return ("", "", 1)
        if command == "which python":
            return ("", "", 1)
        raise AssertionError(f"Unexpected command: {command}")

    connection.exec_command.side_effect = exec_command

    detector = RemoteEnvironmentDetector(connection)
    environments = detector.detect_all_environments()

    assert [env.name for env in environments] == ["base", "torch"]

    conda_info_call = next(
        call for call in connection.exec_command.call_args_list
        if call.args[0] == "/opt/miniconda3/bin/conda info --envs"
    )
    assert conda_info_call.kwargs["timeout"] > connection.config.timeout


def test_batch_check_runicorn_scales_timeout_with_env_count():
    connection = _make_connection(timeout=30)
    connection.exec_command.return_value = (
        "base\t0.5.1\ntorch\t__NOT_INSTALLED__\nvision\t0.5.2\n",
        "",
        0,
    )

    detector = RemoteEnvironmentDetector(connection)
    results = detector.batch_check_runicorn(
        [
            ("base", "/opt/miniconda3/bin/python"),
            ("torch", "/opt/miniconda3/envs/torch/bin/python"),
            ("vision", "/opt/miniconda3/envs/vision/bin/python"),
        ]
    )

    assert results == {
        "base": "0.5.1",
        "torch": None,
        "vision": "0.5.2",
    }
    assert connection.exec_command.call_args.kwargs["timeout"] > connection.config.timeout
