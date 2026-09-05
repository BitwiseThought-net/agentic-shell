"""
Shared fixtures for the test suite.

`shell.py` keeps its runtime state (`ENV_CONFIG`, `AI_AGENTS`) in
module-level globals rather than passing them around explicitly. That's
convenient for a small interactive script, but it means state can leak
between tests unless we reset it. The fixtures below take care of that,
plus a couple of other cross-cutting concerns (isolating the working
directory, making sure `AgenticAI` never actually calls out to a
subprocess or network in tests that don't mean to).
"""
import os
import sys

import pytest

# Make the project root importable regardless of where pytest is invoked from.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import shell  # noqa: E402


@pytest.fixture
def isolated_cwd(tmp_path, monkeypatch):
    """
    Runs a test inside an empty temp directory and chdir's into it.

    `load_env_config` and `load_agent_team` both resolve their default
    filenames (`.env`, `agents.json`) relative to the process's current
    working directory, and `AgenticAI` resolves relative workspace paths
    the same way. Isolating cwd per-test keeps tests from reading/writing
    real repo files or bleeding state into each other.
    """
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture(autouse=True)
def reset_shell_globals():
    """
    Snapshots and restores shell.py's module-level mutable globals so that
    one test populating ENV_CONFIG or AI_AGENTS can never affect another.
    """
    original_env = dict(shell.ENV_CONFIG)
    original_agents = dict(shell.AI_AGENTS)
    yield
    shell.ENV_CONFIG.clear()
    shell.ENV_CONFIG.update(original_env)
    shell.AI_AGENTS.clear()
    shell.AI_AGENTS.update(original_agents)


@pytest.fixture
def make_agent(tmp_path):
    """
    Factory for building an AgenticAI instance with a workspace rooted
    inside the test's tmp_path, so sandboxed command execution never
    touches anything outside of it.
    """
    def _make(name="agent", role="tester", system_prompt="You are a test agent.",
              tools=None, working_directory=None):
        workdir = working_directory or str(tmp_path / "workspace")
        return shell.AgenticAI(
            name=name,
            role=role,
            system_prompt=system_prompt,
            tools=tools if tools is not None else ["all"],
            working_directory=workdir,
        )
    return _make
