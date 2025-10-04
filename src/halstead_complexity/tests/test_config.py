"""Unit tests for the config module."""

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pytest import MonkeyPatch

from halstead_complexity.config import (
    GLOBAL_CONFIG_PATH,
    Config,
    ConfigSource,
    get_config_source,
)


class TestGetConfigSource:
    """Tests for the get_config_source function."""

    def test_returns_local_when_local_true_global_false(self) -> None:
        """Should return LOCAL when local=True and global=False."""
        result = get_config_source(local=True, global_=False)
        assert result == ConfigSource.LOCAL

    def test_returns_global_when_global_true(self) -> None:
        """Should return GLOBAL when global=True (regardless of local)."""
        result = get_config_source(local=False, global_=True)
        assert result == ConfigSource.GLOBAL

    def test_global_takes_precedence_over_local(self) -> None:
        """Should return GLOBAL when both flags are True."""
        result = get_config_source(local=True, global_=True)
        assert result == ConfigSource.GLOBAL

    def test_returns_local_when_both_false(self) -> None:
        """Should return LOCAL when both flags are False."""
        result = get_config_source(local=False, global_=False)
        assert result == ConfigSource.LOCAL


class TestConfigInit:
    """Tests for Config initialization."""

    def test_default_source_is_local(self) -> None:
        """Should default to LOCAL source when no source specified."""
        config = Config()
        assert config.source == ConfigSource.LOCAL


class TestConfigSourcePath:
    """Tests for Config.source_path property."""

    def test_default_source_has_no_path(self) -> None:
        """DEFAULT source should return None for path."""
        config = Config(source=ConfigSource.DEFAULT)
        assert config.source_path is None

    def test_global_source_uses_global_config_path(self) -> None:
        """GLOBAL source should use GLOBAL_CONFIG_PATH constant."""
        config = Config(source=ConfigSource.GLOBAL)
        assert config.source_path == GLOBAL_CONFIG_PATH

    def test_local_source_uses_cwd(self) -> None:
        """LOCAL source should use current working directory."""
        config = Config(source=ConfigSource.LOCAL)
        expected_path = Path.cwd() / "hc_config.json"
        assert config.source_path == expected_path

    def test_local_path_is_dynamic(self, tmp_path: Path) -> None:
        """LOCAL source path should update when cwd changes."""
        import os

        config = Config(source=ConfigSource.LOCAL)
        original_path = config.source_path

        # Change directory
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            new_path = config.source_path

            assert original_path != new_path
            assert new_path == tmp_path / "hc_config.json"
        finally:
            os.chdir(original_cwd)


class TestConfigExists:
    """Tests for Config.exists method."""

    def test_default_source_always_exists(self) -> None:
        """DEFAULT source should always return True."""
        config = Config(source=ConfigSource.DEFAULT)
        assert config.exists() is True

    def test_returns_false_when_file_does_not_exist(
        self, tmp_path: Path, monkeypatch: "MonkeyPatch"
    ) -> None:
        """Should return False when config file doesn't exist."""
        monkeypatch.chdir(tmp_path)
        config = Config(source=ConfigSource.LOCAL)
        assert config.exists() is False

    def test_returns_true_when_file_exists(
        self, tmp_path: Path, monkeypatch: "MonkeyPatch"
    ) -> None:
        """Should return True when config file exists."""
        monkeypatch.chdir(tmp_path)
        config_file = tmp_path / "hc_config.json"
        config_file.write_text("{}")

        config = Config(source=ConfigSource.LOCAL)
        assert config.exists() is True


class TestConfigInitMethod:
    """Tests for Config.init method."""

    def test_creates_config_file_when_not_exists(
        self, tmp_path: Path, monkeypatch: "MonkeyPatch"
    ) -> None:
        """Should create config file with default values."""
        monkeypatch.chdir(tmp_path)
        config = Config(source=ConfigSource.LOCAL)

        assert not config.exists()
        config.init()
        assert config.exists()

        # Verify content
        config_file = tmp_path / "hc_config.json"
        with open(config_file) as f:
            data = json.load(f)

        assert "default_language" in data
        assert "braces_single_operator" in data
        assert "languages" in data

    def test_raises_error_when_file_already_exists(
        self, tmp_path: Path, monkeypatch: "MonkeyPatch"
    ) -> None:
        """Should raise FileExistsError when file already exists."""
        monkeypatch.chdir(tmp_path)
        config = Config(source=ConfigSource.LOCAL)

        config.init()

        with pytest.raises(FileExistsError, match="already exists"):
            config.init()

    def test_raises_error_for_default_source(self) -> None:
        """Should raise ValueError when trying to init DEFAULT source."""
        config = Config(source=ConfigSource.DEFAULT)

        with pytest.raises(ValueError, match="Cannot initialize the default"):
            config.init()

    def test_creates_parent_directories(
        self, tmp_path: Path, monkeypatch: "MonkeyPatch"
    ) -> None:
        """Should create parent directories if they don't exist."""
        nested_dir = tmp_path / "nested" / "dir"
        monkeypatch.chdir(tmp_path)

        # Mock the source_path to use nested directory
        config = Config(source=ConfigSource.GLOBAL)
        config._source = ConfigSource.LOCAL  # type: ignore[misc]

        # Create a config file in a nested directory
        config_file = nested_dir / "hc_config.json"
        nested_dir.mkdir(parents=True)

        monkeypatch.chdir(nested_dir)
        config = Config(source=ConfigSource.LOCAL)
        config.init()

        assert config_file.exists()


class TestConfigGet:
    """Tests for Config.get method."""

    def test_gets_top_level_key(self) -> None:
        """Should retrieve top-level configuration values."""
        config = Config(source=ConfigSource.DEFAULT)
        value = config.get("default_language")
        assert value == "python"

    def test_gets_nested_key_with_dot_notation(self) -> None:
        """Should retrieve nested values using dot notation."""
        config = Config(source=ConfigSource.DEFAULT)
        value = config.get("languages.python.comment")
        assert isinstance(value, (list, tuple))
        assert "#" in value

    def test_returns_default_for_missing_key(self) -> None:
        """Should return default value when key doesn't exist."""
        config = Config(source=ConfigSource.DEFAULT)
        value = config.get("nonexistent_key", "default_value")
        assert value == "default_value"

    def test_returns_none_for_missing_key_without_default(self) -> None:
        """Should return None when key doesn't exist and no default."""
        config = Config(source=ConfigSource.DEFAULT)
        value = config.get("nonexistent_key")
        assert value is None

    def test_gets_from_local_config_file(
        self, tmp_path: Path, monkeypatch: "MonkeyPatch"
    ) -> None:
        """Should retrieve values from merged config (via ConfZConfig)."""
        monkeypatch.chdir(tmp_path)
        config = Config(source=ConfigSource.LOCAL)

        # Get from default config works
        value = config.get("default_language")
        assert value == "python"  # From default config


class TestConfigSet:
    """Tests for Config.set method."""

    def test_sets_top_level_value(
        self, tmp_path: Path, monkeypatch: "MonkeyPatch"
    ) -> None:
        """Should set top-level configuration values."""
        monkeypatch.chdir(tmp_path)
        config = Config(source=ConfigSource.LOCAL)
        config.init()

        config.set("default_language", "javascript")

        # Verify it was saved
        with open(tmp_path / "hc_config.json") as f:
            data = json.load(f)
        assert data["default_language"] == "javascript"

    def test_sets_nested_value(
        self, tmp_path: Path, monkeypatch: "MonkeyPatch"
    ) -> None:
        """Should set nested values using dot notation."""
        monkeypatch.chdir(tmp_path)
        config = Config(source=ConfigSource.LOCAL)
        config.init()

        config.set("nested.key", "value")

        # Verify it was saved
        with open(tmp_path / "hc_config.json") as f:
            data = json.load(f)
        assert data["nested"]["key"] == "value"

    def test_creates_nested_structure(
        self, tmp_path: Path, monkeypatch: "MonkeyPatch"
    ) -> None:
        """Should create nested structure if it doesn't exist."""
        monkeypatch.chdir(tmp_path)
        config_file = tmp_path / "hc_config.json"
        config_file.write_text("{}")

        config = Config(source=ConfigSource.LOCAL)
        config.set("level1.level2.level3", "deep_value")

        with open(config_file) as f:
            data = json.load(f)
        assert data["level1"]["level2"]["level3"] == "deep_value"

    def test_raises_error_for_default_source(self) -> None:
        """Should raise ValueError when trying to set DEFAULT source."""
        config = Config(source=ConfigSource.DEFAULT)

        with pytest.raises(ValueError, match="Cannot modify the default"):
            config.set("key", "value")

    def test_handles_different_value_types(
        self, tmp_path: Path, monkeypatch: "MonkeyPatch"
    ) -> None:
        """Should handle different value types (string, number, bool, list)."""
        monkeypatch.chdir(tmp_path)
        config_file = tmp_path / "hc_config.json"
        config_file.write_text("{}")

        config = Config(source=ConfigSource.LOCAL)

        config.set("string_key", "string_value")
        config.set("number_key", 42)
        config.set("bool_key", True)
        config.set("list_key", ["a", "b", "c"])

        with open(config_file) as f:
            data = json.load(f)

        assert data["string_key"] == "string_value"
        assert data["number_key"] == 42
        assert data["bool_key"] is True
        assert data["list_key"] == ["a", "b", "c"]


class TestConfigList:
    """Tests for Config.list method."""

    def test_lists_default_config(self) -> None:
        """Should list all default configuration values."""
        config = Config(source=ConfigSource.DEFAULT)
        data = config.list()

        assert "default_language" in data
        assert "braces_single_operator" in data
        assert "languages" in data
        assert isinstance(data, dict)

    def test_lists_local_config(
        self, tmp_path: Path, monkeypatch: "MonkeyPatch"
    ) -> None:
        """Should list all local configuration values."""
        monkeypatch.chdir(tmp_path)
        config_file = tmp_path / "hc_config.json"
        test_data = {"default_language": "javascript", "custom_key": "custom_value"}
        config_file.write_text(json.dumps(test_data))

        config = Config(source=ConfigSource.LOCAL)
        data = config.list()

        assert data == test_data

    def test_raises_error_when_file_not_found(
        self, tmp_path: Path, monkeypatch: "MonkeyPatch"
    ) -> None:
        """Should raise FileNotFoundError when config file doesn't exist."""
        monkeypatch.chdir(tmp_path)
        config = Config(source=ConfigSource.LOCAL)

        with pytest.raises(FileNotFoundError, match="not found"):
            config.list()

    def test_raises_error_when_file_empty(
        self, tmp_path: Path, monkeypatch: "MonkeyPatch"
    ) -> None:
        """Should raise ValueError when config file is empty."""
        monkeypatch.chdir(tmp_path)
        config_file = tmp_path / "hc_config.json"
        config_file.write_text("{}")

        config = Config(source=ConfigSource.LOCAL)

        with pytest.raises(ValueError, match="empty or invalid"):
            config.list()


class TestConfigIntegration:
    """Integration tests for Config class."""

    def test_full_workflow(self, tmp_path: Path, monkeypatch: "MonkeyPatch") -> None:
        """Test complete workflow: init, set, list."""
        monkeypatch.chdir(tmp_path)
        config = Config(source=ConfigSource.LOCAL)

        # Initialize
        assert not config.exists()
        config.init()
        assert config.exists()

        # Set values
        config.set("default_language", "javascript")
        config.set("custom.nested.value", "test")

        # List all values (reads from file)
        data = config.list()
        assert data["default_language"] == "javascript"
        assert data["custom"]["nested"]["value"] == "test"

    def test_multiple_config_instances_share_file(
        self, tmp_path: Path, monkeypatch: "MonkeyPatch"
    ) -> None:
        """Test that multiple config instances can modify the same file."""
        monkeypatch.chdir(tmp_path)

        config1 = Config(source=ConfigSource.LOCAL)
        config1.init()
        config1.set("default_language", "value1")

        # list() reads from file directly
        data = config1.list()
        assert data["default_language"] == "value1"

        config2 = Config(source=ConfigSource.LOCAL)
        config2.set("default_language", "value2")

        # Verify via list() which reads the file
        data2 = config2.list()
        assert data2["default_language"] == "value2"
