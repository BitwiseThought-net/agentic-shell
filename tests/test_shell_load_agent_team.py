import json

import shell


VALID_CONFIG = {
    "team_name": "Test Team",
    "agents": [
        {
            "name": "git_guru",
            "role": "Git version control assistant",
            "system_prompt": "You are a git assistant.",
            "allowed_tools": ["git"],
            "working_directory": "./workspace/repo",
        },
        {
            "name": "sys_admin",
            "role": "System diagnostics assistant",
            "system_prompt": "You are a sysadmin.",
            "allowed_tools": ["df", "free"],
            "working_directory": "./workspace/logs",
        },
    ],
}


class TestLoadAgentTeam:
    def test_loads_agents_from_valid_config(self, isolated_cwd):
        config_path = isolated_cwd / "agents.json"
        config_path.write_text(json.dumps(VALID_CONFIG))

        shell.load_agent_team(str(config_path))

        assert set(shell.AI_AGENTS.keys()) == {"git_guru", "sys_admin"}
        assert shell.AI_AGENTS["git_guru"].role == "Git version control assistant"
        assert shell.AI_AGENTS["git_guru"].tools == ["git"]

    def test_agent_names_are_lowercased(self, isolated_cwd):
        config = {
            "team_name": "Test Team",
            "agents": [{
                "name": "GiT_GuRu", "role": "r", "system_prompt": "p",
                "allowed_tools": ["git"], "working_directory": "./workspace/repo",
            }],
        }
        config_path = isolated_cwd / "agents.json"
        config_path.write_text(json.dumps(config))

        shell.load_agent_team(str(config_path))
        assert "git_guru" in shell.AI_AGENTS
        assert "GiT_GuRu" not in shell.AI_AGENTS

    def test_clears_previous_agents_before_loading(self, isolated_cwd):
        config_path = isolated_cwd / "agents.json"
        config_path.write_text(json.dumps(VALID_CONFIG))
        shell.load_agent_team(str(config_path))
        assert len(shell.AI_AGENTS) == 2

        smaller_config = {
            "team_name": "Smaller Team",
            "agents": [VALID_CONFIG["agents"][0]],
        }
        config_path.write_text(json.dumps(smaller_config))
        shell.load_agent_team(str(config_path))
        assert set(shell.AI_AGENTS.keys()) == {"git_guru"}

    def test_missing_file_leaves_existing_agents_untouched(self, isolated_cwd):
        shell.AI_AGENTS.clear()
        shell.AI_AGENTS["preexisting"] = object()

        shell.load_agent_team(str(isolated_cwd / "does_not_exist.json"))

        assert "preexisting" in shell.AI_AGENTS

    def test_missing_file_prints_warning(self, isolated_cwd, capsys):
        shell.load_agent_team(str(isolated_cwd / "does_not_exist.json"))
        out = capsys.readouterr().out
        assert "Failed to load agent configuration" in out

    def test_malformed_json_prints_warning_and_does_not_raise(self, isolated_cwd, capsys):
        config_path = isolated_cwd / "agents.json"
        config_path.write_text("{not valid json")

        shell.load_agent_team(str(config_path))

        out = capsys.readouterr().out
        assert "Failed to load agent configuration" in out

    def test_agent_missing_required_name_key_is_caught(self, isolated_cwd, capsys):
        config = {
            "team_name": "Broken Team",
            "agents": [{"role": "r", "system_prompt": "p", "allowed_tools": ["git"]}],
        }
        config_path = isolated_cwd / "agents.json"
        config_path.write_text(json.dumps(config))

        shell.load_agent_team(str(config_path))

        out = capsys.readouterr().out
        assert "Failed to load agent configuration" in out

    def test_empty_agents_list_results_in_no_agents(self, isolated_cwd):
        config = {"team_name": "Empty Team", "agents": []}
        config_path = isolated_cwd / "agents.json"
        config_path.write_text(json.dumps(config))

        shell.load_agent_team(str(config_path))
        assert shell.AI_AGENTS == {}

    def test_missing_optional_fields_default_sensibly(self, isolated_cwd):
        config = {
            "team_name": "Minimal Team",
            "agents": [{"name": "minimal"}],
        }
        config_path = isolated_cwd / "agents.json"
        config_path.write_text(json.dumps(config))

        shell.load_agent_team(str(config_path))

        agent = shell.AI_AGENTS["minimal"]
        assert agent.role is None
        assert agent.system_prompt is None
        assert agent.tools == []
        assert agent.raw_workspace == "./workspace/default"

    def test_prints_team_name_and_registration_lines(self, isolated_cwd, capsys):
        config_path = isolated_cwd / "agents.json"
        config_path.write_text(json.dumps(VALID_CONFIG))

        shell.load_agent_team(str(config_path))

        out = capsys.readouterr().out
        assert "Test Team" in out
        assert "Registered agent: @git_guru" in out
        assert "Registered agent: @sys_admin" in out
