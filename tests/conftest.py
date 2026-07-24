"""Fixtures for brew-tui's docker-based integration tests.

These tests build the infrastructure/docker image, start a real container, and run
commands *inside* it via `docker exec --user tester`, then check that real `brew`
performed the requested action in the container and that brew-tui's own sqlite DB
(~tester/BrewTuiData/brew.db) was updated to match.

They are slow (image build + a real Homebrew install) and need a working local Docker
daemon with network access, so they are opt-in:

    pytest --run-docker
    pytest --run-docker --formula=jq   # override the formula used (default: hello)

Everything marked `docker` is skipped unless --run-docker is passed.
"""
import shutil
import subprocess
import uuid
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
IMAGE_TAG = "brew-tui:pytest"
DOCKERFILE = REPO_ROOT / "infrastructure" / "docker" / "Dockerfile"


def pytest_addoption(parser):
    parser.addoption(
        "--run-docker",
        action="store_true",
        default=False,
        help="run the real docker-backed integration tests (builds an image, starts "
             "a container, installs real Homebrew + a real formula)",
    )
    parser.addoption(
        "--formula",
        action="store",
        default="hello",
        help="formula to install/list during the docker tests (default: hello)",
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "docker: real docker-backed integration test (needs --run-docker)")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-docker"):
        return
    skip_docker = pytest.mark.skip(reason="pass --run-docker to run real docker integration tests")
    for item in items:
        if "docker" in item.keywords:
            item.add_marker(skip_docker)


def _docker_available() -> bool:
    return shutil.which("docker") is not None


def _run(cmd, timeout=60, **kwargs):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, **kwargs)


def exec_in(container: str, *args: str, timeout: int = 900) -> subprocess.CompletedProcess:
    """Runs a command as `tester` inside `container` and returns the completed process."""
    return _run(["docker", "exec", "--user", "tester", container, *args], timeout=timeout)


@pytest.fixture(scope="session")
def docker_ready():
    if not _docker_available():
        pytest.skip("docker CLI not found on PATH")
    result = _run(["docker", "info"], timeout=15)
    if result.returncode != 0:
        pytest.skip("docker daemon not reachable")
    return True


@pytest.fixture(scope="session")
def image(docker_ready):
    """Builds infrastructure/docker/Dockerfile with repo root as build context."""
    result = _run(
        ["docker", "build", "-f", str(DOCKERFILE), "-t", IMAGE_TAG, str(REPO_ROOT)],
        timeout=1800,
    )
    assert result.returncode == 0, f"image build failed:\n{result.stdout}\n{result.stderr}"
    return IMAGE_TAG


@pytest.fixture(scope="session")
def container(image):
    """Starts one long-lived container shared by the whole docker test session, so
    later tests (list) can see the state earlier tests (install) left behind."""
    name = f"brew-tui-pytest-{uuid.uuid4().hex[:8]}"
    result = _run(["docker", "run", "-d", "--name", name, image, "sleep", "infinity"], timeout=60)
    assert result.returncode == 0, f"container start failed:\n{result.stdout}\n{result.stderr}"
    yield name
    _run(["docker", "rm", "-f", name], timeout=30)
