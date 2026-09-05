import help_manager


class TestDisplayHelp:
    def test_runs_with_no_agents(self, capsys):
        help_manager.display_help()
        out = capsys.readouterr().out
        assert "CUSTOM AGENTIC SHELL" in out
        assert "No active agents running" in out

    def test_runs_with_none_explicitly(self, capsys):
        help_manager.display_help(None)
        out = capsys.readouterr().out
        assert "No active agents running" in out

    def test_runs_with_empty_dict(self, capsys):
        help_manager.display_help({})
        out = capsys.readouterr().out
        assert "No active agents running" in out

    def test_lists_each_active_agent(self, capsys):
        class DummyAgent:
            def __init__(self, role, tools):
                self.role = role
                self.tools = tools

        agents = {
            "git_guru": DummyAgent("Git version control assistant", ["git"]),
            "sys_admin": DummyAgent("System diagnostics assistant", ["df", "free"]),
        }
        help_manager.display_help(agents)
        out = capsys.readouterr().out
        assert "@git_guru" in out
        assert "Git version control assistant" in out
        assert "@sys_admin" in out
        assert "System diagnostics assistant" in out
        assert "No active agents running" not in out

    def test_includes_core_command_reference(self, capsys):
        help_manager.display_help()
        out = capsys.readouterr().out
        for expected in ["help", "cd", "exit / quit", "shell:reload", "shell:addtool"]:
            assert expected in out

    def test_includes_native_fallthrough_section(self, capsys):
        help_manager.display_help()
        out = capsys.readouterr().out
        assert "NATIVE LINUX FALL-THROUGH" in out
