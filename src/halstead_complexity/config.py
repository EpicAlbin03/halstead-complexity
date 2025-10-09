# type: ignore

import json
import os
from enum import Enum
from typing import Any, Dict, Optional

from dynaconf import Dynaconf, Validator
from platformdirs import user_config_dir


class ConfigLevel(Enum):
    """Configuration file precedence levels."""

    DEFAULT = "default"
    GLOBAL = "global"
    LOCAL = "local"


class ConfigError(Exception):
    """Base exception for configuration errors."""

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
    """Manages hierarchical configuration files with precedence: default < global < local."""

    _instance: Optional["ConfigManager"] = None
    _initialized: bool = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        default_file: Optional[str] = None,
        global_file: Optional[str] = None,
        local_file: Optional[str] = None,
    ):
        if self._initialized:
            return

        self.default_file = default_file or os.path.join(
            os.path.dirname(__file__), "default_config.json"
        )
        self.global_file = global_file or os.path.expanduser(
            user_config_dir(appname="halstead-complexity/config.json")
        )
        self.local_file = local_file or os.path.join(os.getcwd(), "hc_config.json")

        self._config_paths = {
            ConfigLevel.DEFAULT: self.default_file,
            ConfigLevel.GLOBAL: self.global_file,
            ConfigLevel.LOCAL: self.local_file,
        }

        self._precedence_order = [
            ConfigLevel.DEFAULT,
            ConfigLevel.GLOBAL,
            ConfigLevel.LOCAL,
        ]

        if not os.path.exists(self.default_file):
            raise ConfigError("Default config file not found", path=self.default_file)

        self._load_configs()
        self._initialized = True

    @classmethod
    def get_instance(
        cls,
        default_file: Optional[str] = None,
        global_file: Optional[str] = None,
        local_file: Optional[str] = None,
    ) -> "ConfigManager":
        """Get or create the singleton ConfigManager instance."""
        if cls._instance is None or not cls._initialized:
            cls._instance = cls(default_file, global_file, local_file)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance. Useful for testing."""
        cls._instance = None
        cls._initialized = False

    def _load_configs(self) -> None:
        """Load all existing configuration files."""
        existing_files = [
            path for path in self._config_paths.values() if os.path.exists(path)
        ]

        if not existing_files:
            raise ConfigError("No configuration files found")

        try:
            self.settings = Dynaconf(
                settings_files=existing_files,
                validators=[
                    Validator(
                        "default_language",
                        must_exist=True,
                        is_in=["python", "javascript"],
                    ),
                ],
            )
        except Exception as e:
            raise ConfigError("Failed to load configuration files", original_error=e)

        self.active_config_file = existing_files[-1]

        if self.active_config_file == self.default_file:
            self.active_config_level = ConfigLevel.DEFAULT
        elif self.active_config_file == self.global_file:
            self.active_config_level = ConfigLevel.GLOBAL
        else:
            self.active_config_level = ConfigLevel.LOCAL

    def get_level_from_flags(
        self, local: bool = False, global_: bool = False
    ) -> ConfigLevel:
        """Determine config level from boolean flags."""
        if local and global_:
            raise ConfigError("Cannot specify both local and global flags")

        if global_:
            return ConfigLevel.GLOBAL
        elif local:
            return ConfigLevel.LOCAL
        return ConfigLevel.DEFAULT

    def get_active_config_level(self) -> ConfigLevel:
        """Get the active config level."""
        return self.active_config_level

    def _find_existing_config(self, max_level: ConfigLevel) -> tuple[str, ConfigLevel]:
        """Find the highest precedence existing config up to max_level."""
        max_index = self._precedence_order.index(max_level)

        for level in reversed(self._precedence_order[: max_index + 1]):
            path = self._config_paths[level]
            if os.path.exists(path):
                return path, level

        raise ConfigError("No configuration file found")

    def _read_config_file(self, path: str) -> Dict[str, Any]:
        """Read and parse a configuration file."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            raise ConfigError("Configuration file not found", path=path)
        except json.JSONDecodeError as e:
            raise ConfigError(
                "Invalid JSON in config file", path=path, original_error=e
            )
        except Exception as e:
            raise ConfigError("Failed to read config file", path=path, original_error=e)

    def _write_config_file(self, path: str, content: str) -> None:
        """Write content to a configuration file."""
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)

            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        except PermissionError as e:
            raise ConfigError(
                "Permission denied writing config", path=path, original_error=e
            )
        except Exception as e:
            raise ConfigError(
                "Failed to write config file", path=path, original_error=e
            )

    def _update_config_file(self, config_path: str, key: str, value: Any) -> None:
        """Update a specific key in a configuration file."""
        try:
            config_data = self._read_config_file(config_path)

            config_data[key] = value

            config_content = json.dumps(config_data, indent=2, ensure_ascii=False)
            self._write_config_file(config_path, config_content)

            self._load_configs()
        except ConfigError:
            raise
        except Exception as e:
            raise ConfigError(
                "Failed to update config file", path=config_path, original_error=e
            )

    def get_config_paths(self) -> Dict[str, str]:
        """Get all configuration file paths."""
        return {level.value: path for level, path in self._config_paths.items()}

    def get_active_config_file(self) -> str:
        """Get the path of the currently active (highest precedence) config file."""
        return self.active_config_file

    def get_config_file_path(
        self, local: bool = False, global_: bool = False
    ) -> tuple[str, bool, str]:
        """
        Get configuration file path based on flags.

        Returns:
            tuple: (path, exists, level_name)
        """
        try:
            requested_level = self.get_level_from_flags(local, global_)

            if requested_level is ConfigLevel.DEFAULT:
                return (self.active_config_file, True, self.active_config_level.value)

            requested_path = self._config_paths[requested_level]

            if os.path.exists(requested_path):
                return (requested_path, True, requested_level.value)

            return (self.active_config_file, False, self.active_config_level.value)
        except ConfigError as e:
            raise ConfigError(f"Failed to get config file path: {e}")

    def get_all_settings(self) -> Dict[str, Any]:
        """Get all settings from merged configuration."""
        try:
            return self.settings.as_dict()
        except Exception as e:
            raise ConfigError(f"Failed to retrieve settings: {e}")

    def get_setting(self, key: str) -> Any:
        """Get a specific setting by key."""
        try:
            value = self.settings.get(key)
            if value is None:
                raise ConfigError(f"Setting '{key}' not found")
            return value
        except ConfigError:
            raise
        except Exception as e:
            raise ConfigError(f"Failed to get setting '{key}': {e}")

    def get_setting_from_flags(
        self, key: str, local: bool = False, global_: bool = False
    ) -> Any:
        """Get a specific setting by key from the specified config level."""
        try:
            requested_level = self.get_level_from_flags(local, global_)
            if requested_level is ConfigLevel.DEFAULT:
                return self.get_setting(key)

            config_path = self._config_paths[requested_level]

            if not os.path.exists(config_path):
                raise ConfigError(
                    f"No {requested_level.value} config file found at {config_path}"
                )

            try:
                level_settings = Dynaconf(settings_files=[config_path])
                return level_settings.get(key)
            except Exception as e:
                raise ConfigError(f"Failed to get setting '{key}': {e}")
        except ConfigError:
            raise
        except Exception as e:
            raise ConfigError(f"Failed to get setting '{key}': {e}")

    def update_setting(self, key: str, value: Any) -> None:
        """Update a setting."""
        try:
            self.settings.update({key: value}, validate=True)
            self._update_config_file(self.active_config_file, key, value)
        except Exception as e:
            raise ConfigError(f"Failed to update setting '{key}': {e}")

    def update_setting_from_flags(
        self, key: str, value: Any, local: bool = False, global_: bool = False
    ) -> None:
        """Update a setting from the specified config level."""
        try:
            requested_level = self.get_level_from_flags(local, global_)
            if requested_level is ConfigLevel.DEFAULT:
                self.update_setting(key, value)
                return

            config_path = self._config_paths[requested_level]

            if not os.path.exists(config_path):
                raise ConfigError(
                    f"No {requested_level.value} config file found at {config_path}"
                )

            try:
                # TODO: update/validate specified config file
                self._update_config_file(config_path, key, value)
            except Exception as e:
                raise ConfigError(f"Failed to update setting '{key}': {e}")
        except ConfigError:
            raise
        except Exception as e:
            raise ConfigError(f"Failed to update setting '{key}': {e}")

    def init_config(self, local: bool = False, global_: bool = False) -> str:
        """
        Initialize a new configuration file at the specified level.

        Returns:
            str: Path to the created config file
        """
        try:
            level = self.get_level_from_flags(local, global_)

            if level is ConfigLevel.DEFAULT:
                raise ConfigError("Must specify either local=True or global_=True")

            target_path = self._config_paths[level]

            if os.path.exists(target_path):
                raise ConfigError(f"Config file already exists at {target_path}")

            with open(self.default_file, "r", encoding="utf-8") as f:
                default_content = f.read()

            self._write_config_file(target_path, default_content)
            self._load_configs()
            return target_path
        except ConfigError:
            raise
        except Exception as e:
            raise ConfigError(f"Failed to initialize config: {e}")

    def list_settings(
        self, local: bool = False, global_: bool = False
    ) -> Dict[str, Any]:
        """
        List settings from a specific configuration level.

        Returns:
            Dict: Settings from the specified config file
        """
        try:
            level = self.get_level_from_flags(local, global_)

            if level is ConfigLevel.DEFAULT:
                return self.get_all_settings()

            config_path = self._config_paths[level]

            if not os.path.exists(config_path):
                raise ConfigError(
                    f"No {level.value} config file found at {config_path}"
                )

            try:
                level_settings = Dynaconf(settings_files=[config_path])
                return level_settings.as_dict()
            except Exception as e:
                raise ConfigError(f"Failed to load {level.value} config: {e}")
        except ConfigError:
            raise
        except Exception as e:
            raise ConfigError(f"Failed to list settings: {e}")
