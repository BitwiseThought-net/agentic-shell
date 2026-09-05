import builtins

import shell


class TestLoadEnvConfig:
    def test_defaults_used_when_file_missing(self, isolated_cwd):
        shell.load_env_config(".env")
        assert shell.ENV_CONFIG == {
            "OLLAMA_HOST": "localhost",
            "OLLAMA_PORT": "11434",
            "OLLAMA_MODEL": "llama3",
        }

    def test_prints_notice_when_file_missing(self, isolated_cwd, capsys):
        shell.load_env_config(".env")
        out = capsys.readouterr().out
        assert ".env" in out
        assert "not found" in out

    def test_overrides_defaults_from_file(self, isolated_cwd):
        env_file = isolated_cwd / ".env"
        env_file.write_text("OLLAMA_HOST=example.internal\nOLLAMA_PORT=9999\n")
        shell.load_env_config(str(env_file))
        assert shell.ENV_CONFIG["OLLAMA_HOST"] == "example.internal"
        assert shell.ENV_CONFIG["OLLAMA_PORT"] == "9999"
        # Untouched default survives.
        assert shell.ENV_CONFIG["OLLAMA_MODEL"] == "llama3"

    def test_adds_arbitrary_new_keys(self, isolated_cwd):
        env_file = isolated_cwd / ".env"
        env_file.write_text("CUSTOM_KEY=custom_value\n")
        shell.load_env_config(str(env_file))
        assert shell.ENV_CONFIG["CUSTOM_KEY"] == "custom_value"

    def test_skips_blank_lines_and_comments(self, isolated_cwd):
        env_file = isolated_cwd / ".env"
        env_file.write_text("\n# a comment\nOLLAMA_MODEL=mixtral\n\n# trailing comment\n")
        shell.load_env_config(str(env_file))
        assert shell.ENV_CONFIG["OLLAMA_MODEL"] == "mixtral"

    def test_strips_surrounding_quotes_from_values(self, isolated_cwd):
        env_file = isolated_cwd / ".env"
        env_file.write_text('OLLAMA_MODEL="mixtral"\nOLLAMA_HOST=\'my-host\'\n')
        shell.load_env_config(str(env_file))
        assert shell.ENV_CONFIG["OLLAMA_MODEL"] == "mixtral"
        assert shell.ENV_CONFIG["OLLAMA_HOST"] == "my-host"

    def test_line_without_equals_sign_is_ignored(self, isolated_cwd):
        env_file = isolated_cwd / ".env"
        env_file.write_text("THIS_LINE_HAS_NO_EQUALS\nOLLAMA_MODEL=phi3\n")
        shell.load_env_config(str(env_file))
        assert "THIS_LINE_HAS_NO_EQUALS" not in shell.ENV_CONFIG
        assert shell.ENV_CONFIG["OLLAMA_MODEL"] == "phi3"

    def test_value_containing_extra_equals_signs_is_preserved(self, isolated_cwd):
        env_file = isolated_cwd / ".env"
        env_file.write_text("SOME_URL=http://host:11434/api?x=1\n")
        shell.load_env_config(str(env_file))
        assert shell.ENV_CONFIG["SOME_URL"] == "http://host:11434/api?x=1"

    def test_clears_previous_config_before_reloading(self, isolated_cwd):
        env_file = isolated_cwd / ".env"
        env_file.write_text("STALE_KEY=stale_value\n")
        shell.load_env_config(str(env_file))
        assert "STALE_KEY" in shell.ENV_CONFIG

        env_file.write_text("OLLAMA_MODEL=llama3\n")
        shell.load_env_config(str(env_file))
        assert "STALE_KEY" not in shell.ENV_CONFIG

    def test_read_error_is_caught_and_reported(self, isolated_cwd, monkeypatch, capsys):
        env_file = isolated_cwd / ".env"
        env_file.write_text("OLLAMA_MODEL=llama3\n")

        real_open = builtins.open

        def boom(path, *args, **kwargs):
            if str(path) == str(env_file):
                raise IOError("disk exploded")
            return real_open(path, *args, **kwargs)

        monkeypatch.setattr(builtins, "open", boom)
        shell.load_env_config(str(env_file))
        out = capsys.readouterr().out
        assert "Error reading environmental configuration file" in out
        # Defaults were still populated before the failed read.
        assert shell.ENV_CONFIG["OLLAMA_MODEL"] == "llama3"
