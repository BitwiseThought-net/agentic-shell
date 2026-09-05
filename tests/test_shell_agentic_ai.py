import os
import shutil
import subprocess
import urllib.error

import pytest

import shell


class TestInit:
    def test_creates_workspace_directory(self, tmp_path):
        target = tmp_path / "nested" / "workspace"
        agent = shell.AgenticAI(
            name="dev", role="developer", system_prompt="prompt",
            tools=["all"], working_directory=str(target),
        )
        assert target.is_dir()
        assert agent.workspace_path == os.path.abspath(str(target))

    def test_defaults_workspace_when_none_given(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        agent = shell.AgenticAI(
            name="dev", role="developer", system_prompt="prompt",
            tools=["all"], working_directory=None,
        )
        assert agent.raw_workspace == "./workspace/default"
        assert agent.workspace_path == os.path.abspath("./workspace/default")
        assert os.path.isdir(agent.workspace_path)

    def test_defaults_workspace_when_empty_string_given(self, tmp_path, monkeypatch):
        # working_directory="" is falsy, same code path as None.
        monkeypatch.chdir(tmp_path)
        agent = shell.AgenticAI(
            name="dev", role="developer", system_prompt="prompt",
            tools=["all"], working_directory="",
        )
        assert agent.raw_workspace == "./workspace/default"

    def test_reuses_existing_directory_without_error(self, tmp_path):
        target = tmp_path / "workspace"
        target.mkdir()
        # Should not raise even though the directory already exists.
        shell.AgenticAI(
            name="dev", role="developer", system_prompt="prompt",
            tools=["all"], working_directory=str(target),
        )

    def test_ollama_url_built_from_env_config(self, make_agent):
        shell.ENV_CONFIG.clear()
        shell.ENV_CONFIG.update({
            "OLLAMA_HOST": "my-host", "OLLAMA_PORT": "1234", "OLLAMA_MODEL": "mixtral",
        })
        agent = make_agent()
        assert agent.ollama_url == "http://my-host:1234/api/generate"
        assert agent.model == "mixtral"

    def test_ollama_url_falls_back_to_defaults_when_env_config_empty(self, make_agent):
        shell.ENV_CONFIG.clear()
        agent = make_agent()
        assert agent.ollama_url == "http://localhost:11434/api/generate"
        assert agent.model == "llama3"

    def test_stores_basic_attributes(self, make_agent):
        agent = make_agent(name="dev", role="developer", tools=["git", "ls"])
        assert agent.name == "dev"
        assert agent.role == "developer"
        assert agent.tools == ["git", "ls"]


class TestExecuteSystemToolPermissions:
    def test_empty_command_rejected(self, make_agent):
        agent = make_agent(tools=["all"])
        assert agent.execute_system_tool("") == "Error: Empty command provided."

    def test_whitespace_only_command_rejected(self, make_agent):
        agent = make_agent(tools=["all"])
        assert agent.execute_system_tool("   ") == "Error: Empty command provided."

    def test_denies_binary_not_in_tool_list(self, make_agent):
        agent = make_agent(name="dev", tools=["git"])
        result = agent.execute_system_tool("docker ps")
        assert "Permission Denied" in result
        assert "@dev" in result
        assert "docker" in result

    def test_allows_binary_explicitly_listed(self, make_agent):
        agent = make_agent(tools=["echo"])
        result = agent.execute_system_tool("echo hi")
        assert "Permission Denied" not in result

    def test_all_grants_any_binary(self, make_agent):
        agent = make_agent(tools=["all"])
        result = agent.execute_system_tool("echo hi")
        assert "Permission Denied" not in result

    def test_missing_binary_reports_system_error(self, make_agent, monkeypatch):
        agent = make_agent(tools=["all"])
        monkeypatch.setattr(shutil, "which", lambda _binary: None)
        result = agent.execute_system_tool("totally_not_a_real_binary")
        assert "System Error" in result
        assert "not found on this system" in result


class TestExecuteSystemToolPathTraversal:
    def test_blocks_dotdot_combined_with_forbidden_path(self, make_agent):
        agent = make_agent(tools=["all"])
        result = agent.execute_system_tool("cat ../ /etc/passwd")
        assert "Path Violation Blocked" in result

    def test_blocks_absolute_forbidden_path(self, make_agent):
        agent = make_agent(tools=["all"])
        result = agent.execute_system_tool("cat /etc/passwd")
        assert "Path Violation Blocked" in result

    def test_blocks_home_directory_reference(self, make_agent):
        agent = make_agent(tools=["all"])
        # Needs a "/" somewhere for the traversal check to even trigger;
        # a bare "~" with no slash is not caught (see the "no slashes" test).
        result = agent.execute_system_tool("cat ~/secrets")
        assert "Path Violation Blocked" in result

    def test_allows_plain_command_with_no_slashes(self, make_agent):
        agent = make_agent(tools=["all"])
        result = agent.execute_system_tool("echo hello")
        assert "Path Violation Blocked" not in result
        assert "hello" in result

    def test_allows_path_inside_own_workspace(self, make_agent, tmp_path):
        agent = make_agent(tools=["all"])
        result = agent.execute_system_tool(f"ls {agent.workspace_path}")
        assert "Path Violation Blocked" not in result


class TestExecuteSystemToolExecution:
    def test_returns_stdout_on_success(self, make_agent):
        agent = make_agent(tools=["all"])
        result = agent.execute_system_tool("echo hello-world")
        assert result.strip() == "hello-world"

    def test_runs_inside_workspace_directory(self, make_agent):
        agent = make_agent(tools=["all"])
        result = agent.execute_system_tool("pwd")
        assert result.strip() == agent.workspace_path

    def test_returns_stderr_on_nonzero_exit(self, make_agent):
        agent = make_agent(tools=["all"])
        result = agent.execute_system_tool("ls nonexistent_file_xyz")
        assert result.strip() != ""

    def test_returns_exit_code_message_when_no_output(self, make_agent):
        agent = make_agent(tools=["all"])
        result = agent.execute_system_tool("true")
        assert "Command completed with exit code 0." in result

    def test_prints_tool_executed_banner(self, make_agent, capsys):
        agent = make_agent(name="dev", tools=["all"])
        agent.execute_system_tool("echo hi")
        out = capsys.readouterr().out
        assert "Tool Executed" in out
        assert "@dev" in out

    def test_timeout_is_caught(self, make_agent, monkeypatch):
        agent = make_agent(tools=["all"])

        def fake_run(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="sleep 100", timeout=30)

        monkeypatch.setattr(subprocess, "run", fake_run)
        result = agent.execute_system_tool("echo hi")
        assert "timed out" in result

    def test_generic_exception_is_caught(self, make_agent, monkeypatch):
        agent = make_agent(tools=["all"])

        def fake_run(*args, **kwargs):
            raise OSError("boom")

        monkeypatch.setattr(subprocess, "run", fake_run)
        result = agent.execute_system_tool("echo hi")
        assert "Execution Error" in result
        assert "boom" in result


class _FakeUrlopenResponse:
    def __init__(self, payload_bytes):
        self._payload_bytes = payload_bytes

    def read(self):
        return self._payload_bytes

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


class TestQueryOllama:
    def test_returns_stripped_response_text(self, make_agent, monkeypatch):
        agent = make_agent()

        def fake_urlopen(req):
            return _FakeUrlopenResponse(b'{"response": "  hello there  "}')

        monkeypatch.setattr(shell.urllib.request, "urlopen", fake_urlopen)
        result = agent.query_ollama("system prompt", "user prompt")
        assert result == "hello there"

    def test_missing_response_key_returns_empty_string(self, make_agent, monkeypatch):
        agent = make_agent()

        def fake_urlopen(req):
            return _FakeUrlopenResponse(b'{}')

        monkeypatch.setattr(shell.urllib.request, "urlopen", fake_urlopen)
        result = agent.query_ollama("system prompt", "user prompt")
        assert result == ""

    def test_url_error_reports_connection_failure(self, make_agent, monkeypatch):
        agent = make_agent()

        def fake_urlopen(req):
            raise urllib.error.URLError("connection refused")

        monkeypatch.setattr(shell.urllib.request, "urlopen", fake_urlopen)
        result = agent.query_ollama("system prompt", "user prompt")
        assert "ERROR_CONNECTION_FAILED" in result
        assert agent.ollama_url in result

    def test_malformed_json_response_reports_parsing_error(self, make_agent, monkeypatch):
        agent = make_agent()

        def fake_urlopen(req):
            return _FakeUrlopenResponse(b"not valid json")

        monkeypatch.setattr(shell.urllib.request, "urlopen", fake_urlopen)
        result = agent.query_ollama("system prompt", "user prompt")
        assert "ERROR_PARSING" in result

    def test_request_body_includes_model_and_prompts(self, make_agent, monkeypatch):
        agent = make_agent()
        captured = {}

        def fake_urlopen(req):
            captured["data"] = req.data
            captured["url"] = req.full_url
            return _FakeUrlopenResponse(b'{"response": "ok"}')

        monkeypatch.setattr(shell.urllib.request, "urlopen", fake_urlopen)
        agent.query_ollama("sys-prompt", "user-prompt")

        import json as _json
        body = _json.loads(captured["data"].decode("utf-8"))
        assert body["system"] == "sys-prompt"
        assert body["prompt"] == "user-prompt"
        assert body["stream"] is False
        assert body["model"] == agent.model
        assert captured["url"] == agent.ollama_url


class TestActivate:
    def test_reports_connection_failure_without_raising(self, make_agent, monkeypatch, capsys):
        agent = make_agent()
        monkeypatch.setattr(
            agent, "query_ollama",
            lambda system_prompt, prompt: "ERROR_CONNECTION_FAILED: nope",
        )
        agent.activate("do something")
        out = capsys.readouterr().out
        assert "ERROR_CONNECTION_FAILED" in out

    def test_executes_tool_when_json_execute_directive_returned(self, make_agent, monkeypatch, capsys):
        agent = make_agent(tools=["all"])
        monkeypatch.setattr(
            agent, "query_ollama",
            lambda system_prompt, prompt: '{"execute": "echo from-agent"}',
        )
        agent.activate("run a command")
        out = capsys.readouterr().out
        assert "System Result" in out
        assert "from-agent" in out

    def test_strips_markdown_json_fences_before_parsing(self, make_agent, monkeypatch, capsys):
        agent = make_agent(tools=["all"])
        monkeypatch.setattr(
            agent, "query_ollama",
            lambda system_prompt, prompt: '```json\n{"execute": "echo fenced"}\n```',
        )
        agent.activate("run a command")
        out = capsys.readouterr().out
        assert "fenced" in out

    def test_plain_text_response_is_printed_as_is(self, make_agent, monkeypatch, capsys):
        agent = make_agent()
        monkeypatch.setattr(
            agent, "query_ollama",
            lambda system_prompt, prompt: "Just a conversational reply.",
        )
        agent.activate("say hello")
        out = capsys.readouterr().out
        assert "Just a conversational reply." in out
        assert "System Result" not in out

    def test_valid_json_without_execute_key_falls_through_to_text(self, make_agent, monkeypatch, capsys):
        agent = make_agent()
        monkeypatch.setattr(
            agent, "query_ollama",
            lambda system_prompt, prompt: '{"note": "no execute key here"}',
        )
        agent.activate("say hello")
        out = capsys.readouterr().out
        assert "System Result" not in out
        assert "no execute key here" in out

    def test_appends_workspace_boundary_to_system_prompt(self, make_agent, monkeypatch):
        agent = make_agent(system_prompt="Base prompt.")
        captured = {}

        def fake_query_ollama(system_prompt, prompt):
            captured["system_prompt"] = system_prompt
            return "a reply"

        monkeypatch.setattr(agent, "query_ollama", fake_query_ollama)
        agent.activate("hello")
        assert "Base prompt." in captured["system_prompt"]
        assert agent.workspace_path in captured["system_prompt"]
