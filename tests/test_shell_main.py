"""
Tests for the interactive `main()` loop.

`main()` blocks on `input()` forever until it sees "exit"/"quit", so every
test here drives it by monkeypatching `builtins.input` with a canned
sequence of commands ending in "exit". `load_env_config`/`load_agent_team`
are exercised for real against an isolated cwd (no .env/agents.json
present), which is a harmless no-op path already covered by their own
test modules.
"""
import builtins

import pytest

import shell
import help_manager


def _feed_inputs(monkeypatch, commands):
    """
    Feeds `commands` to builtins.input() one at a time. An entry that is an
    exception instance is raised instead of returned, so tests can simulate
    Ctrl+D (EOFError) / Ctrl+C (KeyboardInterrupt) at a given point.
    """
    responses = iter(commands)

    def fake_input(prompt=""):
        item = next(responses)
        if isinstance(item, BaseException):
            raise item
        return item

    monkeypatch.setattr(builtins, "input", fake_input)


class TestMainLoopControl:
    def test_exits_cleanly_on_exit_command(self, isolated_cwd, monkeypatch, capsys):
        _feed_inputs(monkeypatch, ["exit"])
        shell.main()
        out = capsys.readouterr().out
        assert "Exiting custom shell." in out

    def test_exits_cleanly_on_quit_command(self, isolated_cwd, monkeypatch, capsys):
        _feed_inputs(monkeypatch, ["quit"])
        shell.main()
        out = capsys.readouterr().out
        assert "Exiting custom shell." in out

    def test_blank_input_is_ignored_and_loop_continues(self, isolated_cwd, monkeypatch, capsys):
        _feed_inputs(monkeypatch, ["", "   ", "exit"])
        shell.main()
        out = capsys.readouterr().out
        assert "Exiting custom shell." in out

    def test_unrecognized_command_does_not_crash(self, isolated_cwd, monkeypatch, capsys):
        _feed_inputs(monkeypatch, ["totally-unknown-command --flag", "exit"])
        shell.main()
        out = capsys.readouterr().out
        assert "Exiting custom shell." in out

    def test_eof_exits_cleanly(self, isolated_cwd, monkeypatch, capsys):
        _feed_inputs(monkeypatch, [EOFError()])
        shell.main()
        out = capsys.readouterr().out
        assert "Exiting custom shell." in out

    def test_keyboard_interrupt_exits_cleanly(self, isolated_cwd, monkeypatch, capsys):
        _feed_inputs(monkeypatch, [KeyboardInterrupt()])
        shell.main()
        out = capsys.readouterr().out
        assert "Exiting custom shell." in out


class TestMainNativeFallThrough:
    def test_unmatched_command_is_forwarded_to_bash(self, isolated_cwd, monkeypatch, capfd):
        _feed_inputs(monkeypatch, ["echo from-native-shell", "exit"])
        shell.main()
        out = capfd.readouterr().out
        # subprocess.run(shell=True) inherits the real stdout fd, so this
        # needs file-descriptor-level capture rather than capsys.
        assert "from-native-shell" in out

    def test_failed_native_command_does_not_crash(self, isolated_cwd, monkeypatch, capsys):
        _feed_inputs(monkeypatch, ["this_binary_does_not_exist_xyz", "exit"])
        shell.main()
        out = capsys.readouterr().out
        assert "Exiting custom shell." in out

    def test_subprocess_error_during_fallthrough_is_reported(self, isolated_cwd, monkeypatch, capsys):
        import subprocess as subprocess_module

        def fake_run(*args, **kwargs):
            raise OSError("could not spawn shell")

        monkeypatch.setattr(subprocess_module, "run", fake_run)
        _feed_inputs(monkeypatch, ["echo hi", "exit"])
        shell.main()
        err = capsys.readouterr().err
        assert "Error: could not spawn shell" in err


class TestMainAgentRouting:
    def test_at_agent_summons_known_agent(self, isolated_cwd, monkeypatch):
        shell.AI_AGENTS.clear()
        agent = shell.AgenticAI(
            name="dev", role="developer", system_prompt="p",
            tools=["all"], working_directory=str(isolated_cwd / "ws"),
        )
        shell.AI_AGENTS["dev"] = agent
        activated_with = {}
        monkeypatch.setattr(agent, "activate", lambda message: activated_with.setdefault("message", message))

        _feed_inputs(monkeypatch, ["@dev check status please", "exit"])
        shell.main()

        assert activated_with["message"] == "check status please"

    def test_at_unknown_agent_reports_not_found(self, isolated_cwd, monkeypatch, capsys):
        shell.AI_AGENTS.clear()
        _feed_inputs(monkeypatch, ["@ghost hello", "exit"])
        shell.main()
        out = capsys.readouterr().out
        assert "@ghost not found" in out


class TestMainHelpCommand:
    def test_help_invokes_display_help(self, isolated_cwd, monkeypatch, capsys):
        called = {}

        def fake_display_help(agents):
            called["agents"] = agents

        monkeypatch.setattr(help_manager, "display_help", fake_display_help)
        _feed_inputs(monkeypatch, ["help", "exit"])
        shell.main()
        assert "agents" in called


class TestMainCdCommand:
    def test_cd_changes_directory(self, isolated_cwd, monkeypatch):
        target = isolated_cwd / "subdir"
        target.mkdir()
        _feed_inputs(monkeypatch, [f"cd {target}", "exit"])
        shell.main()
        import os
        assert os.getcwd() == str(target)

    def test_cd_with_no_args_defaults_to_current_directory(self, isolated_cwd, monkeypatch):
        _feed_inputs(monkeypatch, ["cd", "exit"])
        # Should not raise even with no destination argument.
        shell.main()

    def test_cd_to_nonexistent_directory_reports_error_without_crashing(
        self, isolated_cwd, monkeypatch, capsys,
    ):
        _feed_inputs(monkeypatch, ["cd /no/such/path/xyz", "exit"])
        shell.main()
        err = capsys.readouterr().err
        assert "cd:" in err


class TestMainReloadCommand:
    def test_shell_reload_reloads_env_and_agents(self, isolated_cwd, monkeypatch, capsys):
        env_calls = []
        agent_calls = []
        monkeypatch.setattr(shell, "load_env_config", lambda path: env_calls.append(path))
        monkeypatch.setattr(shell, "load_agent_team", lambda path: agent_calls.append(path))
        _feed_inputs(monkeypatch, ["shell:reload", "exit"])
        shell.main()
        # Called once at startup, once on reload.
        assert env_calls.count(".env") == 2
        assert agent_calls.count("agents.json") == 2
        out = capsys.readouterr().out
        assert "synchronized" in out


class TestMainAddToolCommand:
    def test_addtool_with_missing_args_shows_usage(self, isolated_cwd, monkeypatch, capsys):
        _feed_inputs(monkeypatch, ["shell:addtool", "exit"])
        shell.main()
        out = capsys.readouterr().out
        assert "Usage: shell:addtool" in out

    def test_addtool_with_only_one_arg_shows_usage(self, isolated_cwd, monkeypatch, capsys):
        _feed_inputs(monkeypatch, ["shell:addtool dev", "exit"])
        shell.main()
        out = capsys.readouterr().out
        assert "Usage: shell:addtool" in out

    def test_addtool_adds_new_tool_to_known_agent(self, isolated_cwd, monkeypatch, capsys):
        shell.AI_AGENTS.clear()
        agent = shell.AgenticAI(
            name="dev", role="developer", system_prompt="p",
            tools=["git"], working_directory=str(isolated_cwd / "ws"),
        )
        shell.AI_AGENTS["dev"] = agent

        _feed_inputs(monkeypatch, ["shell:addtool dev docker", "exit"])
        shell.main()

        assert "docker" in agent.tools
        out = capsys.readouterr().out
        assert "Added tool 'docker' to @dev" in out

    def test_addtool_strips_at_symbol_from_agent_name(self, isolated_cwd, monkeypatch):
        shell.AI_AGENTS.clear()
        agent = shell.AgenticAI(
            name="dev", role="developer", system_prompt="p",
            tools=["git"], working_directory=str(isolated_cwd / "ws"),
        )
        shell.AI_AGENTS["dev"] = agent

        _feed_inputs(monkeypatch, ["shell:addtool @dev docker", "exit"])
        shell.main()
        assert "docker" in agent.tools

    def test_addtool_does_not_duplicate_existing_tool(self, isolated_cwd, monkeypatch, capsys):
        shell.AI_AGENTS.clear()
        agent = shell.AgenticAI(
            name="dev", role="developer", system_prompt="p",
            tools=["git"], working_directory=str(isolated_cwd / "ws"),
        )
        shell.AI_AGENTS["dev"] = agent

        _feed_inputs(monkeypatch, ["shell:addtool dev git", "exit"])
        shell.main()

        assert agent.tools.count("git") == 1
        out = capsys.readouterr().out
        assert "already assigned" in out

    def test_addtool_for_unknown_agent_reports_not_found(self, isolated_cwd, monkeypatch, capsys):
        shell.AI_AGENTS.clear()
        _feed_inputs(monkeypatch, ["shell:addtool ghost docker", "exit"])
        shell.main()
        out = capsys.readouterr().out
        assert "@ghost not found" in out
