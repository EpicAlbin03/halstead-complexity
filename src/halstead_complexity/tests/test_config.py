import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generator

import pytest

from ..config import ConfigError, ConfigLevel, ConfigManager, settings


@dataclass
class ConfigScenario:
    """Test scenario config."""

    scenario: str
    local_exists: bool
    global_exists: bool


@pytest.fixture(scope="module")
def default_config_content() -> str:
    """Load the default config content."""
    default_config_path = Path(__file__).parent.parent / "default_config.json"
    with open(default_config_path, "r") as f:
        return f.read()


@pytest.fixture(params=["both", "local_only", "global_only", "none"])
def config_scenario(
    request: pytest.FixtureRequest,
    tmp_path_factory: pytest.TempPathFactory,
    default_config_content: str,
) -> Generator[ConfigScenario, None, None]:
    """
    Configure settings for different test scenarios.

    Scenarios:
    - both: Both local and global configs exist
    - local_only: Only local config exists
    - global_only: Only global config exists
    - none: Only default config exists
    """
    scenario = request.param
    tmp_path = tmp_path_factory.mktemp("config_test")

    local_config = tmp_path / "hc_config.json"
    global_config = tmp_path / "global_config.json"
    default_config = tmp_path / "default_config.json"

    default_config.write_text(default_config_content)

    if scenario in ["both", "local_only"]:
        local_config.write_text(default_config_content)
    if scenario in ["both", "global_only"]:
        global_config.write_text(default_config_content)

    settings.configure(
        default_file=str(default_config),
        local_file=str(local_config),
        global_file=str(global_config),
    )

    yield ConfigScenario(
        scenario=scenario,
        local_exists=local_config.exists(),
        global_exists=global_config.exists(),
    )


class TestGetConfigFilePath:
    """Test get_config_file_path with various flag combinations."""

    def test_get_config_file_path_flags_none(
        self, config_scenario: ConfigScenario
    ) -> None:
        """Test path resolution with no flags (should return active config)."""
        path, exists, config_type = settings.get_config_file_path()

        if config_scenario.scenario == "both":
            assert config_type == "local"
            assert exists is True
            assert path == settings.config_paths[ConfigLevel.LOCAL]
        elif config_scenario.scenario == "local_only":
            assert config_type == "local"
            assert exists is True
            assert path == settings.config_paths[ConfigLevel.LOCAL]
        elif config_scenario.scenario == "global_only":
            assert config_type == "global"
            assert exists is True
            assert path == settings.config_paths[ConfigLevel.GLOBAL]
        elif config_scenario.scenario == "none":
            assert config_type == "default"
            assert exists is True
            assert path == settings.config_paths[ConfigLevel.DEFAULT]

    def test_get_config_file_path_flags_global(
        self, config_scenario: ConfigScenario
    ) -> None:
        """Test path resolution with global flag."""
        path, exists, config_type = settings.get_config_file_path(global_=True)
        global_path = settings.config_paths[ConfigLevel.GLOBAL]

        if config_scenario.scenario in ["both", "global_only"]:
            assert config_type == "global"
            assert exists is True
            assert path == global_path
        elif config_scenario.scenario == "local_only":
            assert config_type == "local"
            assert exists is False
            assert path == settings.config_paths[ConfigLevel.LOCAL]
        elif config_scenario.scenario == "none":
            assert config_type == "default"
            assert exists is False
            assert path == settings.config_paths[ConfigLevel.DEFAULT]

    def test_get_config_file_path_flags_local(
        self, config_scenario: ConfigScenario
    ) -> None:
        """Test path resolution with local flag."""
        path, exists, config_type = settings.get_config_file_path(local=True)
        local_path = settings.config_paths[ConfigLevel.LOCAL]

        if config_scenario.scenario in ["both", "local_only"]:
            assert config_type == "local"
            assert exists is True
            assert path == local_path
        elif config_scenario.scenario == "global_only":
            assert config_type == "global"
            assert exists is False
            assert path == settings.config_paths[ConfigLevel.GLOBAL]
        elif config_scenario.scenario == "none":
            assert config_type == "default"
            assert exists is False
            assert path == settings.config_paths[ConfigLevel.DEFAULT]

    def test_get_config_file_path_flags_both(self) -> None:
        """Test path resolution with both flags (should raise error)."""
        with pytest.raises(ConfigError, match="Cannot specify both"):
            settings.get_config_file_path(local=True, global_=True)


class TestGetActiveConfigLevel:
    """Test get_active_config_level with various scenarios."""

    def test_get_active_config_level_both(
        self, config_scenario: ConfigScenario
    ) -> None:
        """Test that active config level is correctly identified."""
        active_level = settings.active_config_level

        if config_scenario.scenario == "both":
            assert active_level == ConfigLevel.LOCAL
        elif config_scenario.scenario == "local_only":
            assert active_level == ConfigLevel.LOCAL
        elif config_scenario.scenario == "global_only":
            assert active_level == ConfigLevel.GLOBAL
        elif config_scenario.scenario == "none":
            assert active_level == ConfigLevel.DEFAULT


class TestGetLevelFromFlags:
    """Test get_level_from_flags with various flag combinations."""

    def test_get_level_from_flags_both(self) -> None:
        """Test that using both flags raises an error."""
        with pytest.raises(ConfigError, match="Cannot specify both"):
            settings.get_level_from_flags(local=True, global_=True)

    def test_get_level_from_flags_global(self) -> None:
        """Test getting level from global flag."""
        level = settings.get_level_from_flags(global_=True)
        assert level == ConfigLevel.GLOBAL

    def test_get_level_from_flags_local(self) -> None:
        """Test getting level from local flag."""
        level = settings.get_level_from_flags(local=True)
        assert level == ConfigLevel.LOCAL

    def test_get_level_from_flags_none(self, config_scenario: ConfigScenario) -> None:
        """Test getting level with no flags returns active level."""
        level = settings.get_level_from_flags()
        assert level == settings.active_config_level


class TestGetAllSettings:
    """Test get_all_settings functionality."""

    def test_get_all_settings(self, config_scenario: ConfigScenario) -> None:
        """Test retrieving all settings."""
        all_settings = settings.get_all_settings()
        assert isinstance(all_settings, dict)
        assert len(all_settings) > 0

    def test_get_all_settings_contains_default_language(
        self, config_scenario: ConfigScenario
    ) -> None:
        """Test that merged settings contain default_language."""
        all_settings = settings.get_all_settings()
        assert "default_language" in all_settings
        assert all_settings["default_language"] in ["python", "javascript"]


class TestGetSetting:
    """Test get_setting functionality."""

    def test_get_setting_existing(self, config_scenario: ConfigScenario) -> None:
        """Test retrieving a specific setting."""
        value = settings.get_setting("default_language")
        assert value is not None
        assert value in ["python", "javascript"]

    def test_get_setting_nonexistent(self, config_scenario: ConfigScenario) -> None:
        """Test retrieving a nonexistent setting raises error."""
        with pytest.raises(ConfigError, match="not found"):
            settings.get_setting("nonexistent_key_12345")


class TestGetSettingFromFlags:
    """Test get_setting_from_flags with various flag combinations."""

    def test_get_setting_from_flags_none(self, config_scenario: ConfigScenario) -> None:
        """Test getting setting with no flags returns from merged config."""
        value = settings.get_setting_from_flags("default_language")
        assert value is not None
        assert value in ["python", "javascript"]

    def test_get_setting_from_flags_local(
        self, config_scenario: ConfigScenario
    ) -> None:
        """Test getting setting with local flag."""
        if config_scenario.scenario in ["both", "local_only"]:
            value = settings.get_setting_from_flags("default_language", local=True)
            assert value is not None
        else:
            value = settings.get_setting_from_flags("default_language", local=True)
            assert value is None

    def test_get_setting_from_flags_global(
        self, config_scenario: ConfigScenario
    ) -> None:
        """Test getting setting with global flag."""
        if config_scenario.scenario in ["both", "global_only"]:
            value = settings.get_setting_from_flags("default_language", global_=True)
            assert value is not None
        else:
            value = settings.get_setting_from_flags("default_language", global_=True)
            assert value is None

    def test_get_setting_from_flags_both(self) -> None:
        """Test getting setting with both flags raises error."""
        with pytest.raises(ConfigError, match="Cannot specify both"):
            settings.get_setting_from_flags(
                "default_language", local=True, global_=True
            )


class TestListSettings:
    """Test list_settings with various flag combinations."""

    def test_list_settings_flags_none(self, config_scenario: ConfigScenario) -> None:
        """Test listing settings with no flags returns merged config."""
        listed = settings.list_settings()
        all_settings = settings.get_all_settings()
        assert listed == all_settings

    def test_list_settings_flags_local(self, config_scenario: ConfigScenario) -> None:
        """Test listing settings with local flag."""
        if config_scenario.scenario in ["both", "local_only"]:
            listed = settings.list_settings(local=True)
            assert isinstance(listed, dict)
            assert "default_language" in listed
        else:
            with pytest.raises(ConfigError, match="No local config"):
                settings.list_settings(local=True)

    def test_list_settings_flags_global(self, config_scenario: ConfigScenario) -> None:
        """Test listing settings with global flag."""
        if config_scenario.scenario in ["both", "global_only"]:
            listed = settings.list_settings(global_=True)
            assert isinstance(listed, dict)
            assert "default_language" in listed
        else:
            with pytest.raises(ConfigError, match="No global config"):
                settings.list_settings(global_=True)

    def test_list_settings_flags_both(self) -> None:
        """Test listing settings with both flags raises error."""
        with pytest.raises(ConfigError, match="Cannot specify both"):
            settings.list_settings(local=True, global_=True)


class TestUpdateSetting:
    """Test update_setting functionality."""

    def test_update_setting_active_config(
        self, config_scenario: ConfigScenario
    ) -> None:
        """Test updating a setting in active config."""
        if config_scenario.scenario == "none":
            pytest.skip("Cannot update default config directly")

        original_value = settings.get_setting("default_language")
        new_value = "javascript" if original_value == "python" else "python"

        settings.update_setting("default_language", new_value)

        assert settings.get_setting("default_language") == new_value

        settings.update_setting("default_language", original_value)

    def test_update_setting_preserves_other_settings(
        self, config_scenario: ConfigScenario
    ) -> None:
        """Test that updating one setting preserves others."""
        if config_scenario.scenario == "none":
            pytest.skip("Cannot update default config directly")

        original_settings = settings.get_all_settings()
        original_value = settings.get_setting("default_language")
        new_value = "javascript" if original_value == "python" else "python"

        settings.update_setting("default_language", new_value)

        updated_settings = settings.get_all_settings()

        for key in original_settings:
            if key != "default_language":
                assert updated_settings[key] == original_settings[key]

        settings.update_setting("default_language", original_value)


class TestUpdateSettingFromFlags:
    """Test update_setting_from_flags with various flag combinations."""

    def test_update_setting_from_flags_none(
        self, config_scenario: ConfigScenario
    ) -> None:
        """Test updating setting with no flags updates active config."""
        if config_scenario.scenario == "none":
            pytest.skip("Cannot update default config directly")

        original_value = settings.get_setting("default_language")
        new_value = "javascript" if original_value == "python" else "python"

        settings.update_setting_from_flags("default_language", new_value)
        assert settings.get_setting("default_language") == new_value

        settings.update_setting_from_flags("default_language", original_value)

    def test_update_setting_from_flags_local(
        self, config_scenario: ConfigScenario
    ) -> None:
        """Test updating setting with local flag."""
        if config_scenario.scenario in ["both", "local_only"]:
            original_value = settings.get_setting_from_flags(
                "default_language", local=True
            )
            new_value = "javascript" if original_value == "python" else "python"

            settings.update_setting_from_flags(
                "default_language", new_value, local=True
            )

            updated_value = settings.get_setting_from_flags(
                "default_language", local=True
            )
            assert updated_value == new_value

            settings.update_setting_from_flags(
                "default_language", original_value, local=True
            )
        else:
            with pytest.raises(ConfigError, match="No local config"):
                settings.update_setting_from_flags(
                    "default_language", "python", local=True
                )

    def test_update_setting_from_flags_global(
        self, config_scenario: ConfigScenario
    ) -> None:
        """Test updating setting with global flag."""
        if config_scenario.scenario in ["both", "global_only"]:
            original_value = settings.get_setting_from_flags(
                "default_language", global_=True
            )
            new_value = "javascript" if original_value == "python" else "python"

            settings.update_setting_from_flags(
                "default_language", new_value, global_=True
            )

            updated_value = settings.get_setting_from_flags(
                "default_language", global_=True
            )
            assert updated_value == new_value

            settings.update_setting_from_flags(
                "default_language", original_value, global_=True
            )
        else:
            with pytest.raises(ConfigError, match="No global config"):
                settings.update_setting_from_flags(
                    "default_language", "python", global_=True
                )

    def test_update_setting_from_flags_both(self) -> None:
        """Test updating setting with both flags raises error."""
        with pytest.raises(ConfigError, match="Cannot specify both"):
            settings.update_setting_from_flags(
                "default_language", "python", local=True, global_=True
            )

    def test_update_setting_from_flags_default_config(
        self, config_scenario: ConfigScenario
    ) -> None:
        """Test updating a setting in default config raises error."""
        if config_scenario.scenario != "none":
            pytest.skip("Cannot update default config directly")

        with pytest.raises(ConfigError, match="Cannot update default config"):
            settings.update_setting_from_flags("default_language", "python")


class TestInitConfig:
    """Test init_config with various flag combinations."""

    def test_init_config_flags_none(self) -> None:
        """Test that init without flags raises an error."""
        with pytest.raises(ConfigError, match="Must specify either"):
            settings.init_config()

    def test_init_config_flags_local(self, tmp_path: Path) -> None:
        """Test initializing a local config file."""
        test_local = tmp_path / "test_local.json"
        test_global = tmp_path / "test_global.json"
        test_default = tmp_path / "test_default.json"

        default_path = Path(__file__).parent.parent / "default_config.json"
        test_default.write_text(default_path.read_text())

        temp_settings = ConfigManager(
            default_file=str(test_default),
            global_file=str(test_global),
            local_file=str(test_local),
        )

        created_path = temp_settings.init_config(local=True)

        assert created_path == str(test_local)
        assert test_local.exists()

        local_data = json.loads(test_local.read_text())
        default_data = json.loads(test_default.read_text())
        assert local_data == default_data

    def test_init_config_flags_global(self, tmp_path: Path) -> None:
        """Test initializing a global config file."""
        test_local = tmp_path / "test_local.json"
        test_global = tmp_path / "test_global.json"
        test_default = tmp_path / "test_default.json"

        default_path = Path(__file__).parent.parent / "default_config.json"
        test_default.write_text(default_path.read_text())

        temp_settings = ConfigManager(
            default_file=str(test_default),
            global_file=str(test_global),
            local_file=str(test_local),
        )

        created_path = temp_settings.init_config(global_=True)

        assert created_path == str(test_global)
        assert test_global.exists()

        global_data = json.loads(test_global.read_text())
        default_data = json.loads(test_default.read_text())
        assert global_data == default_data

    def test_init_config_flags_both(self) -> None:
        """Test initializing with both flags raises error."""
        with pytest.raises(ConfigError, match="Cannot specify both"):
            settings.init_config(local=True, global_=True)

    def test_init_config_already_exists_local(
        self, config_scenario: ConfigScenario
    ) -> None:
        """Test that initializing an existing local config raises an error."""
        if config_scenario.scenario in ["both", "local_only"]:
            with pytest.raises(ConfigError, match="already exists"):
                settings.init_config(local=True)

    def test_init_config_already_exists_global(
        self, config_scenario: ConfigScenario
    ) -> None:
        """Test that initializing an existing global config raises an error."""
        if config_scenario.scenario in ["both", "global_only"]:
            with pytest.raises(ConfigError, match="already exists"):
                settings.init_config(global_=True)


class TestGetConfigPaths:
    """Test get_config_paths functionality."""

    def test_get_config_paths_returns_all_levels(
        self, config_scenario: ConfigScenario
    ) -> None:
        """Test getting all config paths."""
        paths = settings.get_config_paths()

        assert "default" in paths
        assert "global" in paths
        assert "local" in paths
        assert len(paths) == 3

    def test_get_config_paths_values_are_strings(
        self, config_scenario: ConfigScenario
    ) -> None:
        """Test that all path values are strings."""
        paths = settings.get_config_paths()

        for level, path in paths.items():
            assert isinstance(level, str)
            assert isinstance(path, str)


class TestGetActiveConfigFile:
    """Test get_active_config_file functionality."""

    def test_get_active_config_file_exists(
        self, config_scenario: ConfigScenario
    ) -> None:
        """Test getting the active config file path."""
        active_file = settings.active_config_file

        assert active_file is not None
        assert Path(active_file).exists()

    def test_get_active_config_file_matches_level(
        self, config_scenario: ConfigScenario
    ) -> None:
        """Test that active file matches the expected active level."""
        active_file = settings.active_config_file
        active_level = settings.active_config_level
        expected_path = settings.config_paths[active_level]

        assert active_file == expected_path

    def test_get_active_config_file_precedence(
        self, config_scenario: ConfigScenario
    ) -> None:
        """Test that active config respects precedence order."""
        active_level = settings.active_config_level

        if config_scenario.scenario == "both":
            assert active_level == ConfigLevel.LOCAL
        elif config_scenario.scenario == "local_only":
            assert active_level == ConfigLevel.LOCAL
        elif config_scenario.scenario == "global_only":
            assert active_level == ConfigLevel.GLOBAL
        elif config_scenario.scenario == "none":
            assert active_level == ConfigLevel.DEFAULT


class TestConfigConfigure:
    """Test configure method functionality."""

    def test_configure_updates_paths(self, tmp_path: Path) -> None:
        """Test that configure updates config paths."""
        test_local = tmp_path / "new_local.json"
        test_global = tmp_path / "new_global.json"
        test_default = tmp_path / "new_default.json"

        default_path = Path(__file__).parent.parent / "default_config.json"
        test_default.write_text(default_path.read_text())

        temp_settings = ConfigManager(
            default_file=str(test_default),
            global_file=str(test_global),
            local_file=str(test_local),
        )

        original_paths = temp_settings.get_config_paths()

        new_local = tmp_path / "updated_local.json"
        new_global = tmp_path / "updated_global.json"

        temp_settings.configure(
            local_file=str(new_local),
            global_file=str(new_global),
        )

        updated_paths = temp_settings.get_config_paths()

        assert updated_paths["local"] == str(new_local)
        assert updated_paths["global"] == str(new_global)
        assert updated_paths["default"] == original_paths["default"]


class TestConfigError:
    """Test ConfigError exception behavior."""

    def test_config_error_with_message_only(self) -> None:
        """Test ConfigError with just a message."""
        error = ConfigError("Test error")
        assert str(error) == "Test error"

    def test_config_error_with_path(self) -> None:
        """Test ConfigError with message and path."""
        error = ConfigError("Test error", path="/some/path")
        assert "Test error" in str(error)
        assert "/some/path" in str(error)

    def test_config_error_with_original_error(self) -> None:
        """Test ConfigError with original exception."""
        original = ValueError("Original error")
        error = ConfigError("Test error", original_error=original)
        assert "Test error" in str(error)
        assert "Original error" in str(error)

    def test_config_error_with_all_parameters(self) -> None:
        """Test ConfigError with all parameters."""
        original = ValueError("Original error")
        error = ConfigError("Test error", path="/some/path", original_error=original)
        error_str = str(error)
        assert "Test error" in error_str
        assert "/some/path" in error_str
        assert "Original error" in error_str


class TestLanguageValidation:
    """Test language configuration validation."""

    def test_valid_language_config(self, tmp_path: Path) -> None:
        """Test that valid language configurations pass validation."""
        valid_config: dict[str, Any] = {
            "default_language": "python",
            "braces_single_operator": False,
            "template_literal_single_operand": False,
            "languages": {
                "python": {
                    "comment": ["#"],
                    "extensions": [".py"],
                    "excluded": ["__pycache__"],
                    "statement_types": ["expression_statement"],
                    "operand_types": ["identifier"],
                    "keywords": ["def", "class"],
                    "symbols": ["(", ")"],
                    "multi_word_operators": [],
                    "multi_line_delimiters": [{"start": '"""', "end": '"""'}],
                }
            },
        }

        config_file = tmp_path / "test_config.json"
        config_file.write_text(json.dumps(valid_config))

        # Should not raise any errors
        config_manager = ConfigManager(
            default_file=str(config_file),
            global_file=str(tmp_path / "nonexistent_global.json"),
            local_file=str(tmp_path / "nonexistent_local.json"),
        )
        assert config_manager.get_setting("default_language") == "python"

    def test_missing_language_field(self, tmp_path: Path) -> None:
        """Test that missing required language fields raise errors."""
        invalid_config: dict[str, Any] = {
            "default_language": "python",
            "braces_single_operator": False,
            "template_literal_single_operand": False,
            "languages": {
                "python": {
                    "comment": ["#"],
                    "extensions": [".py"],
                    # Missing required fields
                }
            },
        }

        config_file = tmp_path / "test_config.json"
        config_file.write_text(json.dumps(invalid_config))

        with pytest.raises(ConfigError, match="missing required field"):
            ConfigManager(
                default_file=str(config_file),
                global_file=str(tmp_path / "nonexistent_global.json"),
                local_file=str(tmp_path / "nonexistent_local.json"),
            )

    def test_invalid_field_type(self, tmp_path: Path) -> None:
        """Test that invalid field types raise errors."""
        invalid_config: dict[str, Any] = {
            "default_language": "python",
            "braces_single_operator": False,
            "template_literal_single_operand": False,
            "languages": {
                "python": {
                    "comment": "#",  # Should be a list, not a string
                    "extensions": [".py"],
                    "excluded": ["__pycache__"],
                    "statement_types": ["expression_statement"],
                    "operand_types": ["identifier"],
                    "keywords": ["def", "class"],
                    "symbols": ["(", ")"],
                    "multi_word_operators": [],
                    "multi_line_delimiters": [{"start": '"""', "end": '"""'}],
                }
            },
        }

        config_file = tmp_path / "test_config.json"
        config_file.write_text(json.dumps(invalid_config))

        with pytest.raises(ConfigError, match="must be a list"):
            ConfigManager(
                default_file=str(config_file),
                global_file=str(tmp_path / "nonexistent_global.json"),
                local_file=str(tmp_path / "nonexistent_local.json"),
            )

    def test_invalid_multi_line_delimiters(self, tmp_path: Path) -> None:
        """Test that invalid multi_line_delimiters structure raises errors."""
        invalid_config: dict[str, Any] = {
            "default_language": "python",
            "braces_single_operator": False,
            "template_literal_single_operand": False,
            "languages": {
                "python": {
                    "comment": ["#"],
                    "extensions": [".py"],
                    "excluded": ["__pycache__"],
                    "statement_types": ["expression_statement"],
                    "operand_types": ["identifier"],
                    "keywords": ["def", "class"],
                    "symbols": ["(", ")"],
                    "multi_word_operators": [],
                    "multi_line_delimiters": [{"start": '"""'}],  # Missing 'end'
                }
            },
        }

        config_file = tmp_path / "test_config.json"
        config_file.write_text(json.dumps(invalid_config))

        with pytest.raises(ConfigError, match="must have both 'start' and 'end'"):
            ConfigManager(
                default_file=str(config_file),
                global_file=str(tmp_path / "nonexistent_global.json"),
                local_file=str(tmp_path / "nonexistent_local.json"),
            )

    def test_multiple_languages_validation(self, tmp_path: Path) -> None:
        """Test validation works with multiple language configs."""
        valid_config: dict[str, Any] = {
            "default_language": "python",
            "braces_single_operator": False,
            "template_literal_single_operand": False,
            "languages": {
                "python": {
                    "comment": ["#"],
                    "extensions": [".py"],
                    "excluded": ["__pycache__"],
                    "statement_types": ["expression_statement"],
                    "operand_types": ["identifier"],
                    "keywords": ["def", "class"],
                    "symbols": ["(", ")"],
                    "multi_word_operators": [],
                    "multi_line_delimiters": [{"start": '"""', "end": '"""'}],
                },
                "javascript": {
                    "comment": ["//"],
                    "extensions": [".js"],
                    "excluded": ["node_modules"],
                    "statement_types": ["variable_declaration"],
                    "operand_types": ["identifier"],
                    "keywords": ["function", "const"],
                    "symbols": ["(", ")"],
                    "multi_word_operators": [],
                    "multi_line_delimiters": [{"start": "/*", "end": "*/"}],
                },
            },
        }

        config_file = tmp_path / "test_config.json"
        config_file.write_text(json.dumps(valid_config))

        # Should not raise any errors
        config_manager = ConfigManager(
            default_file=str(config_file),
            global_file=str(tmp_path / "nonexistent_global.json"),
            local_file=str(tmp_path / "nonexistent_local.json"),
        )
        assert "python" in config_manager.get_setting("languages")
        assert "javascript" in config_manager.get_setting("languages")

    def test_custom_language_name(self, tmp_path: Path) -> None:
        """Test that custom language names are supported."""
        valid_config: dict[str, Any] = {
            "default_language": "rust",
            "braces_single_operator": False,
            "template_literal_single_operand": False,
            "languages": {
                "rust": {  # Custom language name
                    "comment": ["//"],
                    "extensions": [".rs"],
                    "excluded": ["target"],
                    "statement_types": ["expression_statement"],
                    "operand_types": ["identifier"],
                    "keywords": ["fn", "let"],
                    "symbols": ["(", ")"],
                    "multi_word_operators": [],
                    "multi_line_delimiters": [{"start": "/*", "end": "*/"}],
                }
            },
        }

        config_file = tmp_path / "test_config.json"
        config_file.write_text(json.dumps(valid_config))

        # Should not raise any errors
        config_manager = ConfigManager(
            default_file=str(config_file),
            global_file=str(tmp_path / "nonexistent_global.json"),
            local_file=str(tmp_path / "nonexistent_local.json"),
        )
        assert config_manager.get_setting("default_language") == "rust"
        assert "rust" in config_manager.get_setting("languages")
