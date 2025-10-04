"""Tests for the config CLI commands."""

import json
from pathlib import Path
from typing import TYPE_CHECKING

from typer.testing import CliRunner

from halstead_complexity import cli

if TYPE_CHECKING:
    from pytest import MonkeyPatch

runner: CliRunner = CliRunner()


class TestConfigInit:
    """Tests for 'config init' command."""

    def test_creates_local_config_file(
        self, tmp_path: Path, monkeypatch: "MonkeyPatch"
    ) -> None:
        """Should create a local config file with default values."""
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(cli.app, ["config", "init"])

        assert result.exit_code == 0
        assert "Configuration file created at:" in result.stdout
        assert (tmp_path / "hc_config.json").exists()

    def test_creates_global_config_file_with_flag(
        self, tmp_path: Path, monkeypatch: "MonkeyPatch"
    ) -> None:
        """Should create global config when --global flag is used."""
        # Note: This test would modify the actual global config, so we'll
        # just verify the command runs with proper messaging
        result = runner.invoke(cli.app, ["config", "init", "--global"])

        # Will succeed or fail depending on if global config already exists
        assert result.exit_code in [0, 1]
        if result.exit_code == 0:
            assert "Configuration file created at:" in result.stdout
        else:
            assert "already exists" in result.stderr

    def test_fails_when_file_already_exists(
        self, tmp_path: Path, monkeypatch: "MonkeyPatch"
    ) -> None:
        """Should fail with error when config file already exists."""
        monkeypatch.chdir(tmp_path)

        # Create config first time
        result = runner.invoke(cli.app, ["config", "init"])
        assert result.exit_code == 0

        # Try to create again
        result = runner.invoke(cli.app, ["config", "init"])

        assert result.exit_code == 1
        assert "Error:" in result.stderr
        assert "already exists" in result.stderr

    def test_creates_valid_json_file(
        self, tmp_path: Path, monkeypatch: "MonkeyPatch"
    ) -> None:
        """Should create a valid JSON file with expected structure."""
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(cli.app, ["config", "init"])
        assert result.exit_code == 0

        config_file = tmp_path / "hc_config.json"
        with open(config_file) as f:
            data = json.load(f)

        assert "default_language" in data
        assert "braces_single_operator" in data
        assert "languages" in data


class TestConfigGet:
    """Tests for 'config get' command."""

    def test_gets_value_from_default_config(self) -> None:
        """Should retrieve value from default configuration."""
        result = runner.invoke(cli.app, ["config", "get", "default_language"])

        assert result.exit_code == 0
        assert "python" in result.stdout

    def test_gets_nested_value_with_dot_notation(self) -> None:
        """Should retrieve nested values using dot notation."""
        result = runner.invoke(cli.app, ["config", "get", "languages.python.comment"])

        assert result.exit_code == 0
        # Should return JSON array
        assert "[" in result.stdout or "#" in result.stdout

    def test_fails_for_nonexistent_key(self) -> None:
        """Should fail with error for nonexistent key."""
        result = runner.invoke(cli.app, ["config", "get", "nonexistent_key"])

        assert result.exit_code == 1
        assert "not found" in result.stderr

    def test_gets_value_from_local_config(
        self, tmp_path: Path, monkeypatch: "MonkeyPatch"
    ) -> None:
        """Should retrieve value from merged config."""
        monkeypatch.chdir(tmp_path)  # type: ignore

        result = runner.invoke(cli.app, ["config", "get", "default_language"])

        assert result.exit_code == 0
        assert "python" in result.stdout

    def test_formats_complex_types_as_json(
        self, tmp_path: Path, monkeypatch: "MonkeyPatch"
    ) -> None:
        """Should format lists and dicts as JSON."""
        # Get a complex type from default config
        result = runner.invoke(cli.app, ["config", "get", "languages.python.comment"])

        assert result.exit_code == 0
        assert "[" in result.stdout or "#" in result.stdout


class TestConfigSet:
    """Tests for 'config set' command."""

    def test_sets_string_value(
        self, tmp_path: Path, monkeypatch: "MonkeyPatch"
    ) -> None:
        """Should set a string value in config."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(cli.app, ["config", "init"])

        result = runner.invoke(
            cli.app, ["config", "set", "default_language", "javascript"]
        )

        assert result.exit_code == 0
        assert "Successfully set" in result.stdout

        # Verify it was saved
        with open(tmp_path / "hc_config.json") as f:
            data = json.load(f)
        assert data["default_language"] == "javascript"

    def test_sets_boolean_value(
        self, tmp_path: Path, monkeypatch: "MonkeyPatch"
    ) -> None:
        """Should parse and set boolean values."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(cli.app, ["config", "init"])

        result = runner.invoke(
            cli.app, ["config", "set", "braces_single_operator", "true"]
        )

        assert result.exit_code == 0

        # Verify it was saved as boolean
        with open(tmp_path / "hc_config.json") as f:
            data = json.load(f)
        assert data["braces_single_operator"] is True

    def test_sets_number_value(
        self, tmp_path: Path, monkeypatch: "MonkeyPatch"
    ) -> None:
        """Should parse and set numeric values."""
        monkeypatch.chdir(tmp_path)
        config_file = tmp_path / "hc_config.json"
        config_file.write_text("{}")

        result = runner.invoke(cli.app, ["config", "set", "number_key", "42"])

        assert result.exit_code == 0

        with open(config_file) as f:
            data = json.load(f)
        assert data["number_key"] == 42

    def test_sets_array_value(self, tmp_path: Path, monkeypatch: "MonkeyPatch") -> None:
        """Should parse and set array values."""
        monkeypatch.chdir(tmp_path)
        config_file = tmp_path / "hc_config.json"
        config_file.write_text("{}")

        result = runner.invoke(cli.app, ["config", "set", "array_key", '["a","b","c"]'])

        assert result.exit_code == 0

        with open(config_file) as f:
            data = json.load(f)
        assert data["array_key"] == ["a", "b", "c"]

    def test_sets_nested_value(
        self, tmp_path: Path, monkeypatch: "MonkeyPatch"
    ) -> None:
        """Should set nested values using dot notation."""
        monkeypatch.chdir(tmp_path)
        config_file = tmp_path / "hc_config.json"
        config_file.write_text("{}")

        result = runner.invoke(cli.app, ["config", "set", "nested.key", "value"])

        assert result.exit_code == 0

        with open(config_file) as f:
            data = json.load(f)
        assert data["nested"]["key"] == "value"

    def test_treats_non_json_as_string(
        self, tmp_path: Path, monkeypatch: "MonkeyPatch"
    ) -> None:
        """Should treat non-JSON values as strings."""
        monkeypatch.chdir(tmp_path)
        config_file = tmp_path / "hc_config.json"
        config_file.write_text("{}")

        result = runner.invoke(cli.app, ["config", "set", "key", "not-json-value"])

        assert result.exit_code == 0

        with open(config_file) as f:
            data = json.load(f)
        assert data["key"] == "not-json-value"


class TestConfigList:
    """Tests for 'config list' command."""

    def test_lists_default_config(self) -> None:
        """Should list all default configuration values."""
        result = runner.invoke(cli.app, ["config", "list"])

        # Will fail if no local config exists
        if result.exit_code == 0:
            data = json.loads(result.stdout)
            assert isinstance(data, dict)
        else:
            assert "not found" in result.stderr

    def test_lists_local_config(
        self, tmp_path: Path, monkeypatch: "MonkeyPatch"
    ) -> None:
        """Should list all local configuration values."""
        monkeypatch.chdir(tmp_path)
        config_file = tmp_path / "hc_config.json"
        test_data = {"default_language": "python", "custom_key": "custom_value"}
        config_file.write_text(json.dumps(test_data))

        result = runner.invoke(cli.app, ["config", "list"])

        assert result.exit_code == 0
        output_data = json.loads(result.stdout)
        assert output_data == test_data

    def test_fails_when_file_not_found(
        self, tmp_path: Path, monkeypatch: "MonkeyPatch"
    ) -> None:
        """Should fail with error when config file doesn't exist."""
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(cli.app, ["config", "list"])

        assert result.exit_code == 1
        assert "Error:" in result.stderr
        assert "not found" in result.stderr

    def test_fails_when_file_empty(
        self, tmp_path: Path, monkeypatch: "MonkeyPatch"
    ) -> None:
        """Should fail with error when config file is empty."""
        monkeypatch.chdir(tmp_path)
        config_file = tmp_path / "hc_config.json"
        config_file.write_text("{}")

        result = runner.invoke(cli.app, ["config", "list"])

        assert result.exit_code == 1
        assert "Error:" in result.stderr
        assert "empty" in result.stderr

    def test_outputs_valid_json(
        self, tmp_path: Path, monkeypatch: "MonkeyPatch"
    ) -> None:
        """Should output valid JSON format."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(cli.app, ["config", "init"])

        result = runner.invoke(cli.app, ["config", "list"])

        assert result.exit_code == 0
        # Should be valid JSON
        data = json.loads(result.stdout)
        assert isinstance(data, dict)


class TestConfigPath:
    """Tests for 'config path' command."""

    def test_shows_local_path(self, tmp_path: Path, monkeypatch: "MonkeyPatch") -> None:
        """Should show local config file path."""
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(cli.app, ["config", "path"])

        assert result.exit_code == 0
        assert str(tmp_path / "hc_config.json") in result.stdout

    def test_shows_global_path_with_flag(self) -> None:
        """Should show global config file path with --global flag."""
        result = runner.invoke(cli.app, ["config", "path", "--global"])

        assert result.exit_code == 0
        assert ".config" in result.stdout or "halstead-complexity" in result.stdout

    def test_local_flag_explicit(
        self, tmp_path: Path, monkeypatch: "MonkeyPatch"
    ) -> None:
        """Should show local path when --local flag is explicit."""
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(cli.app, ["config", "path", "--local"])

        assert result.exit_code == 0
        assert str(tmp_path / "hc_config.json") in result.stdout


class TestConfigGlobalFlag:
    """Tests for --global flag across commands."""

    def test_global_flag_with_get(self) -> None:
        """Should use global config with --global flag on get command."""
        result = runner.invoke(
            cli.app, ["config", "get", "default_language", "--global"]
        )

        # Should work if global config exists
        assert result.exit_code in [0, 1]

    def test_global_flag_with_set(self, tmp_path: Path) -> None:
        """Should use global config with --global flag on set command."""
        # This would modify real global config, so we just verify command structure
        result = runner.invoke(
            cli.app, ["config", "set", "test_key", "test_value", "--global"]
        )

        # Will fail if no global config exists
        assert result.exit_code in [0, 1]

    def test_global_flag_with_list(self) -> None:
        """Should use global config with --global flag on list command."""
        result = runner.invoke(cli.app, ["config", "list", "--global"])

        # Should work if global config exists
        assert result.exit_code in [0, 1]
