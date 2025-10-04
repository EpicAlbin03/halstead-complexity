from __future__ import annotations

import json
from enum import Enum
from importlib import resources
from pathlib import Path
from typing import Any, Dict, Optional

from confz import BaseConfig, FileFormat, FileSource
from platformdirs import user_config_dir
from pydantic import BaseModel, ConfigDict, Field


class MultiLineDelimiter(BaseModel):
    """Model representing multi-line comment delimiters."""

    model_config = ConfigDict(frozen=True)

    start: str
    end: str


class LanguageConfig(BaseModel):
    """Model representing configuration for a specific programming language."""

    model_config = ConfigDict(frozen=True)

    comment: tuple[str, ...] = Field(default_factory=tuple)
    extensions: tuple[str, ...] = Field(default_factory=tuple)
    excluded: tuple[str, ...] = Field(default_factory=tuple)
    statement_types: tuple[str, ...] = Field(default_factory=tuple)
    operand_types: tuple[str, ...] = Field(default_factory=tuple)
    keywords: tuple[str, ...] = Field(default_factory=tuple)
    symbols: tuple[str, ...] = Field(default_factory=tuple)
    multi_word_operators: tuple[str, ...] = Field(default_factory=tuple)
    multi_line_delimiters: tuple[MultiLineDelimiter, ...] = Field(default_factory=tuple)


def _load_default_config_bytes() -> bytes:
    """Load the default configuration JSON from package resources."""
    try:
        content = (
            resources.files(__package__).joinpath("default_config.json").read_bytes()
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "Default configuration file is missing from the package."
        ) from exc
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Default configuration contains invalid JSON.") from exc
    if not isinstance(data, dict):
        raise RuntimeError("Default configuration must be a JSON object.")
    return content


DEFAULT_CONFIG_BYTES = _load_default_config_bytes()

GLOBAL_CONFIG_PATH = (
    Path(user_config_dir(appname="halstead-complexity")) / "config.json"
)


class ConfZConfig(BaseConfig):
    """Configuration model for halstead-complexity using ConfZ."""

    default_language: str
    braces_single_operator: bool
    template_literal_single_operand: bool
    languages: Dict[str, LanguageConfig]

    CONFIG_SOURCES = [
        FileSource(file=DEFAULT_CONFIG_BYTES, format=FileFormat.JSON),
        FileSource(
            file=user_config_dir(appname="halstead-complexity/config.json"),
            optional=True,
        ),
        FileSource(file=Path.cwd() / "hc_config.json", optional=True),
    ]


class ConfigSource(Enum):
    """Enumeration of available configuration sources."""

    DEFAULT = "default"
    GLOBAL = "global"
    LOCAL = "local"


def get_config_source(local: bool, global_: bool) -> ConfigSource:
    """
    Determine the configuration source based on the CLI flags.

    Args:
        local: Whether --local flag is set
        global_: Whether --global flag is set

    Returns:
        The appropriate ConfigSource
    """
    if global_:
        return ConfigSource.GLOBAL
    return ConfigSource.LOCAL


class Config:
    """Configuration manager that tracks the current config source and provides access methods."""

    def __init__(self, source: ConfigSource = ConfigSource.LOCAL):
        """
        Initialize the Config manager.

        Args:
            source: The configuration source to use (default, global, or local)
        """
        self._source = source
        self._config = ConfZConfig()
        self._config_data: Optional[Dict[str, Any]] = None

    @property
    def source(self) -> ConfigSource:
        """Get the current configuration source."""
        return self._source

    @property
    def source_path(self) -> Optional[Path]:
        """Get the path to the current configuration file."""
        if self._source == ConfigSource.DEFAULT:
            return None
        elif self._source == ConfigSource.GLOBAL:
            return GLOBAL_CONFIG_PATH
        else:  # LOCAL
            return Path.cwd() / "hc_config.json"

    def _load_config_file(self) -> Dict[str, Any]:
        """Load configuration from the current source file."""
        if self._source == ConfigSource.DEFAULT:
            return json.loads(DEFAULT_CONFIG_BYTES)

        path = self.source_path
        if path and path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_config_file(self, data: Dict[str, Any]) -> None:
        """Save configuration to the current source file."""
        if self._source == ConfigSource.DEFAULT:
            raise ValueError("Cannot modify the default configuration")

        path = self.source_path
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value by key.

        Args:
            key: Dot-separated key path (e.g., "default_language" or "languages.python.keywords")
            default: Default value to return if key is not found

        Returns:
            The configuration value or default if not found
        """
        keys = key.split(".")

        # Read from the specific source file only (not merged config)
        config_data = self._load_config_file()
        if not config_data:
            # File doesn't exist or is empty, fall back to merged config
            value: Any = self._config
            try:
                for k in keys:
                    if hasattr(value, k):  # type: ignore[arg-type]
                        value = getattr(value, k)  # type: ignore[arg-type]
                    elif isinstance(value, dict):
                        value = value[k]  # type: ignore[index]
                    else:
                        return default
                return value  # type: ignore[return-value]
            except (KeyError, AttributeError, IndexError):
                return default

        # Navigate through the config data from the specific file
        value = config_data
        try:
            for k in keys:
                if isinstance(value, dict):
                    value = value[k]  # type: ignore[index]
                else:
                    return default
            return value  # type: ignore[return-value]
        except (KeyError, TypeError):
            return default

    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.

        Args:
            key: Dot-separated key path (e.g., "default_language" or "languages.python.comment")
            value: The value to set

        Raises:
            ValueError: If trying to modify the default configuration
        """
        if self._source == ConfigSource.DEFAULT:
            raise ValueError("Cannot modify the default configuration")

        # Load current config from file
        config_data = self._load_config_file()

        # Navigate to the correct nested location and set the value
        keys = key.split(".")
        current = config_data

        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]

        # Set the final value
        current[keys[-1]] = value

        # Save back to file
        self._save_config_file(config_data)

        # Reload the ConfZConfig to reflect changes
        self._config = ConfZConfig()

    def list(self) -> Dict[str, Any]:
        """
        List all configuration values from the current source.

        Returns:
            Dictionary containing all configuration values

        Raises:
            FileNotFoundError: If the configuration file doesn't exist (for non-default sources)
        """
        if self._source == ConfigSource.DEFAULT:
            return json.loads(DEFAULT_CONFIG_BYTES)

        # Load from current source file
        path = self.source_path
        if not path or not path.exists():
            raise FileNotFoundError(
                f"Configuration file not found at {path}. "
                f"Use 'init' command to create it."
            )

        file_config = self._load_config_file()

        # If file is empty, raise an error
        if not file_config:
            raise ValueError(
                f"Configuration file at {path} is empty or invalid. "
                f"Use 'init' command to reinitialize it."
            )

        return file_config

    def init(self) -> None:
        """
        Initialize a configuration file at the current source location.

        Creates a new configuration file with default values if it doesn't exist.

        Raises:
            ValueError: If trying to initialize the default configuration
        """
        if self._source == ConfigSource.DEFAULT:
            raise ValueError("Cannot initialize the default configuration")

        path = self.source_path
        if path and not path.exists():
            # Create with default configuration
            default_config = json.loads(DEFAULT_CONFIG_BYTES)
            self._save_config_file(default_config)
        elif path and path.exists():
            raise FileExistsError(f"Configuration file already exists at {path}")

    def exists(self) -> bool:
        """Check if the configuration file exists at the current source."""
        if self._source == ConfigSource.DEFAULT:
            return True
        path = self.source_path
        return path.exists() if path else False
