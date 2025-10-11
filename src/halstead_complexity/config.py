# type: ignore

import json
import os
import sys
from enum import Enum
from typing import Any, Dict, Optional

from dynaconf import Dynaconf
from platformdirs import user_config_dir


class ConfigLevel(Enum):
    """Config file precedence levels."""

    DEFAULT = "default"
    GLOBAL = "global"
    LOCAL = "local"


class ConfigError(Exception):
    """Base exception for config errors."""

    def __init__(
        self,
        message: str,
        path: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        self.message = message
        self.path = path
        self.original_error = original_error
        super().__init__(self.message)

    def __str__(self) -> str:
        parts = [self.message]
        if self.path:
            parts.append(f"Path: {self.path}")
        if self.original_error:
            parts.append(f"Cause: {self.original_error}")
        return " | ".join(parts)


class ConfigManager:
    """Manages hierarchical config files with precedence: default < global < local."""

    PRECEDENCE_ORDER = [ConfigLevel.DEFAULT, ConfigLevel.GLOBAL, ConfigLevel.LOCAL]

    def __init__(
        self,
        default_file: Optional[str] = None,
        global_file: Optional[str] = None,
        local_file: Optional[str] = None,
    ):
        self.config_paths = {
            ConfigLevel.DEFAULT: default_file or self._get_default_path(),
            ConfigLevel.GLOBAL: global_file or self._get_global_path(),
            ConfigLevel.LOCAL: local_file or self._get_local_path(),
        }

        self._validate_default_exists()
        self._load_configs()

    @staticmethod
    def _get_default_path() -> str:
        """Get the default config file path."""
        return os.path.join(os.path.dirname(__file__), "default_config.json")

    @staticmethod
    def _get_global_path() -> str:
        """Get the global config file path."""
        return os.path.join(
            user_config_dir(appname="halstead-complexity"), "config.json"
        )

    @staticmethod
    def _get_local_path() -> str:
        """Get the local config file path."""
        return os.path.join(os.getcwd(), "hc_config.json")

    def _validate_default_exists(self) -> None:
        """Ensure the default config file exists."""
        default_path = self.config_paths[ConfigLevel.DEFAULT]
        if not os.path.exists(default_path):
            raise ConfigError("Default config file not found", path=default_path)

    def _load_configs(self) -> None:
        """Load all existing config files using Dynaconf's settings_files."""
        existing_files = [
            path for path in self.config_paths.values() if os.path.exists(path)
        ]

        if not existing_files:
            raise ConfigError("No config files found")

        try:
            self.settings = Dynaconf(
                settings_files=existing_files,
                environments=False,
            )
        except Exception as e:
            raise ConfigError("Failed to load config files", original_error=e)

        self._validate_language_configs()

        self.active_config_file = existing_files[-1]
        self.active_config_level = self._determine_active_level()

    def _determine_active_level(self) -> ConfigLevel:
        """Determine the active config level based on the active file."""
        for level, path in self.config_paths.items():
            if path == self.active_config_file:
                return level
        return ConfigLevel.DEFAULT

    def _validate_config_data(self, config_data: Dict[str, Any]) -> None:
        """Validate configuration data structure without loading into Dynaconf.

        This is used to validate config before writing to file.
        """
        # Validate required top-level fields
        if "languages" not in config_data:
            raise ConfigError("Missing 'languages' in configuration")

        languages = config_data["languages"]
        if not isinstance(languages, dict):
            raise ConfigError("'languages' must be a dictionary")

        # Validate default_language
        default_language = config_data.get("default_language")
        if default_language is None:
            raise ConfigError("Missing 'default_language' in configuration")
        if default_language not in languages:
            raise ConfigError(
                f"default_language '{default_language}' is not defined in languages"
            )

        # Validate boolean fields
        braces_single_operator = config_data.get("braces_single_operator", False)
        if not isinstance(braces_single_operator, bool):
            raise ConfigError(
                f"braces_single_operator must be of type bool, got {type(braces_single_operator).__name__}"
            )

        template_literal_single_operand = config_data.get(
            "template_literal_single_operand", False
        )
        if not isinstance(template_literal_single_operand, bool):
            raise ConfigError(
                f"template_literal_single_operand must be of type bool, got {type(template_literal_single_operand).__name__}"
            )

        # Validate language configurations
        required_fields = [
            "comment",
            "extensions",
            "excluded",
            "statement_types",
            "operand_types",
            "keywords",
            "symbols",
            "multi_word_operators",
            "multi_line_delimiters",
        ]

        for lang_name, lang_config in languages.items():
            if not isinstance(lang_config, dict):
                raise ConfigError(
                    f"Language '{lang_name}' configuration must be a dictionary"
                )

            for field in required_fields:
                if field not in lang_config:
                    raise ConfigError(
                        f"Language '{lang_name}' is missing required field '{field}'"
                    )

            list_fields = [
                "comment",
                "extensions",
                "excluded",
                "statement_types",
                "operand_types",
                "keywords",
                "symbols",
                "multi_word_operators",
                "multi_line_delimiters",
            ]

            for field in list_fields:
                if field in lang_config and not isinstance(lang_config[field], list):
                    raise ConfigError(
                        f"Language '{lang_name}' field '{field}' must be a list, "
                        f"got {type(lang_config[field]).__name__}"
                    )

            if "multi_line_delimiters" in lang_config:
                for idx, delimiter in enumerate(lang_config["multi_line_delimiters"]):
                    if not isinstance(delimiter, dict):
                        raise ConfigError(
                            f"Language '{lang_name}' multi_line_delimiters[{idx}] "
                            f"must be a dictionary with 'start' and 'end' keys"
                        )
                    if "start" not in delimiter or "end" not in delimiter:
                        raise ConfigError(
                            f"Language '{lang_name}' multi_line_delimiters[{idx}] "
                            f"must have both 'start' and 'end' keys"
                        )

    def _validate_language_configs(self) -> None:
        """Validate each language configuration dynamically from loaded settings."""
        if not hasattr(self.settings, "languages"):
            raise ConfigError("Missing 'languages' in configuration")

        config_data = {k.lower(): v for k, v in self.settings.as_dict().items()}
        self._validate_config_data(config_data)

    def configure(
        self,
        default_file: Optional[str] = None,
        global_file: Optional[str] = None,
        local_file: Optional[str] = None,
    ) -> None:
        """Reconfigure the settings instance. Useful for testing."""
        if default_file:
            self.config_paths[ConfigLevel.DEFAULT] = default_file
        if global_file:
            self.config_paths[ConfigLevel.GLOBAL] = global_file
        if local_file:
            self.config_paths[ConfigLevel.LOCAL] = local_file

        self._load_configs()

    def get_level_from_flags(
        self, local: bool = False, global_: bool = False
    ) -> ConfigLevel:
        """Determine config level from boolean flags."""
        if local and global_:
            raise ConfigError("Cannot specify both local and global flags")

        if global_:
            return ConfigLevel.GLOBAL
        if local:
            return ConfigLevel.LOCAL
        return self.active_config_level

    def _read_config_file(self, path: str) -> Dict[str, Any]:
        """Read and parse a config file."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            raise ConfigError("Config file not found", path=path)
        except json.JSONDecodeError as e:
            raise ConfigError(
                "Invalid JSON in config file", path=path, original_error=e
            )
        except Exception as e:
            raise ConfigError("Failed to read config file", path=path, original_error=e)

    def _write_config_file(self, path: str, data: Dict[str, Any]) -> None:
        """Write content to a config file."""
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                f.write("\n")
        except PermissionError as e:
            raise ConfigError(
                "Permission denied writing config", path=path, original_error=e
            )
        except Exception as e:
            raise ConfigError(
                "Failed to write config file", path=path, original_error=e
            )

    def _update_config_file(self, config_path: str, key: str, value: Any) -> None:
        """Update a specific key in a config file."""
        config_data = self._read_config_file(config_path)

        # Handle nested keys with dot notation
        if "." in key:
            keys = key.split(".")
            current = config_data

            # Navigate to the parent of the target key
            for k in keys[:-1]:
                if k not in current:
                    current[k] = {}
                elif not isinstance(current[k], dict):
                    raise ConfigError(
                        f"Cannot set nested key '{key}': '{k}' is not a dictionary"
                    )
                current = current[k]

            # Set the final key
            current[keys[-1]] = value
        else:
            config_data[key] = value

        self._validate_config_data(config_data)
        self._write_config_file(config_path, config_data)
        self._load_configs()

    def _get_config_at_level(self, level: ConfigLevel) -> Dict[str, Any]:
        """Load and return settings from a specific config level."""
        config_path = self.config_paths[level]

        if not os.path.exists(config_path):
            raise ConfigError(f"No {level.value} config file found at {config_path}")

        try:
            level_settings = Dynaconf(settings_files=[config_path])
            return {k.lower(): v for k, v in level_settings.as_dict().items()}
        except Exception as e:
            raise ConfigError(f"Failed to load {level.value} config: {e}")

    def get_config_paths(self) -> Dict[str, str]:
        """Get all config file paths."""
        return {level.value: path for level, path in self.config_paths.items()}

    def get_config_file_path(
        self, local: bool = False, global_: bool = False
    ) -> tuple[str, bool, str]:
        """
        Get config file path based on flags.

        Returns:
            tuple: (path, exists, level_name)
        """
        requested_level = self.get_level_from_flags(local, global_)
        requested_path = self.config_paths[requested_level]
        exists = os.path.exists(requested_path)

        if not exists and requested_level != self.active_config_level:
            return (
                self.active_config_file,
                False,
                self.active_config_level.value,
            )

        return (requested_path, exists, requested_level.value)

    def get_all_settings(self) -> Dict[str, Any]:
        """Get all settings from merged config."""
        return {k.lower(): v for k, v in self.settings.as_dict().items()}

    def get_setting(self, key: str) -> Any:
        """Get a specific setting by key."""
        value = self.settings.get(key)
        if value is None:
            raise ConfigError(f"Setting '{key}' not found")
        return value

    def get_setting_from_flags(
        self, key: str, local: bool = False, global_: bool = False
    ) -> Any:
        """Get a specific setting by key from the specified config level.

        Returns None if the config file doesn't exist or the key is not found.
        """
        requested_level = self.get_level_from_flags(local, global_)

        if requested_level == self.active_config_level and not (local or global_):
            return self.get_setting(key)

        config_path = self.config_paths[requested_level]
        if not os.path.exists(config_path):
            return None

        level_settings = Dynaconf(settings_files=[config_path])
        return level_settings.get(key)

    def find_setting_source(self, key: str) -> str:
        """Find which config level a setting comes from.

        Args:
            key: The setting key to look for

        Returns:
            The name of the config level where the setting is defined
        """
        # Check in reverse precedence order (local -> global -> default)
        for level in reversed(self.PRECEDENCE_ORDER):
            config_path = self.config_paths[level]
            if os.path.exists(config_path):
                try:
                    level_settings = Dynaconf(settings_files=[config_path])
                    value = level_settings.get(key)
                    if value is not None:
                        return level.value
                except Exception:
                    continue

        return "default"

    def update_setting(self, key: str, value: Any, path: str = None) -> None:
        """Update a setting in the active config file."""
        try:
            self.settings.update({key: value}, validate=True)
        except Exception as e:
            raise ConfigError(str(e))

        if not path:
            path = self.active_config_file

        self._update_config_file(path, key, value)

    def update_setting_from_flags(
        self, key: str, value: Any, local: bool = False, global_: bool = False
    ) -> None:
        """Update a setting at the specified config level."""
        requested_level = self.get_level_from_flags(local, global_)

        if requested_level == ConfigLevel.DEFAULT and not (local or global_):
            raise ConfigError(
                "Cannot update default config. Create a config by running 'config init' first."
            )

        config_path = self.config_paths[requested_level]
        if not os.path.exists(config_path):
            raise ConfigError(
                f"No {requested_level.value} config file found at {config_path}"
            )

        self.update_setting(key, value, config_path)

    def init_config(self, local: bool = False, global_: bool = False) -> str:
        """
        Initialize a new config file at the specified level.

        Returns:
            str: Path to the created config file
        """
        if not local and not global_:
            raise ConfigError("Must specify either local=True or global_=True")

        level = self.get_level_from_flags(local, global_)
        target_path = self.config_paths[level]

        if os.path.exists(target_path):
            raise ConfigError(f"Config file already exists at {target_path}")

        default_content = self._read_config_file(self.config_paths[ConfigLevel.DEFAULT])
        self._write_config_file(target_path, default_content)
        self._load_configs()

        return target_path

    def list_settings(
        self, local: bool = False, global_: bool = False
    ) -> Dict[str, Any]:
        """List settings from a specific config level."""
        level = self.get_level_from_flags(local, global_)

        if not local and not global_:
            return self.get_all_settings()

        return self._get_config_at_level(level)


try:
    settings = ConfigManager()
except ConfigError as e:
    print(f"\033[91m✗ Config error: {e.message}\033[0m", file=sys.stderr)
    if e.path:
        print(f"  Path: {e.path}", file=sys.stderr)
    sys.exit(1)
