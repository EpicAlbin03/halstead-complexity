from __future__ import annotations

import json
from enum import Enum
from importlib import resources
from pathlib import Path
from typing import Any, Dict, Optional

from confz import BaseConfig, FileFormat, FileSource
from platformdirs import user_config_dir
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from typing_extensions import Self


class MultiLineDelimiter(BaseModel):
    model_config = ConfigDict(frozen=True)

    start: str
    end: str


class LanguageConfig(BaseModel):
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

    @field_validator("extensions")
    @classmethod
    def validate_extensions(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        for ext in value:
            if not ext.startswith("."):
                raise ValueError(f"File extension '{ext}' must start with a dot (.)")
        return value

    @field_validator(
        "comment",
        "extensions",
        "statement_types",
        "operand_types",
        "keywords",
        "symbols",
        "multi_line_delimiters",
    )
    @classmethod
    def validate_not_empty(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) == 0:
            raise ValueError("This field cannot be empty")
        return value


def _load_default_config_bytes() -> bytes:
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

GLOBAL_CONFIG_PATH: Path = (
    Path(user_config_dir(appname="halstead-complexity")) / "config.json"
)


def _get_local_config_path() -> Path:
    return Path.cwd() / "hc_config.json"


class ConfZConfig(BaseConfig):
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
        FileSource(file=_get_local_config_path(), optional=True),
    ]

    @model_validator(mode="after")
    def validate_default_language_exists(self) -> Self:
        if self.default_language not in self.languages:
            raise ValueError(
                f"default_language '{self.default_language}' must be defined in languages. "
                f"Available languages: {', '.join(self.languages.keys())}"
            )
        return self

    @field_validator("languages")
    @classmethod
    def validate_languages_not_empty(
        cls, v: Dict[str, LanguageConfig]
    ) -> Dict[str, LanguageConfig]:
        if len(v) == 0:
            raise ValueError("At least one language must be configured")
        return v


class ConfigSource(Enum):
    DEFAULT = "default"
    GLOBAL = "global"
    LOCAL = "local"


def get_config_source(local: bool, global_: bool) -> ConfigSource:
    if global_:
        return ConfigSource.GLOBAL
    elif local:
        return ConfigSource.LOCAL
    return ConfigSource.DEFAULT


class Config:
    def __init__(self, source: ConfigSource = ConfigSource.DEFAULT):
        self._source = source
        self._config = ConfZConfig()

    @property
    def source(self) -> ConfigSource:
        return self._source

    @property
    def source_path(self) -> Optional[Path]:
        if self.source == ConfigSource.LOCAL:
            return _get_local_config_path()
        elif self.source == ConfigSource.GLOBAL:
            return GLOBAL_CONFIG_PATH
        else:
            return None

    @property
    def requested_source_path(self) -> Optional[Path]:
        """Return the path for the requested source, without fallback logic."""
        if self._source == ConfigSource.LOCAL:
            return _get_local_config_path()
        elif self._source == ConfigSource.GLOBAL:
            return GLOBAL_CONFIG_PATH
        else:
            return None

    def _save_config_file(self, data: Dict[str, Any]) -> None:
        if self._source == ConfigSource.DEFAULT:
            raise ValueError("Cannot modify the default configuration")

        path = self.requested_source_path
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

        self._config = ConfZConfig()

    def get(self, key: str) -> Any:
        keys = key.split(".")
        value: Any = self._config

        try:
            for k in keys:
                if hasattr(value, k):  # type: ignore
                    value = getattr(value, k)  # type: ignore
                elif isinstance(value, dict):
                    value = value[k]  # type: ignore
                else:
                    return None
            return value  # type: ignore
        except (KeyError, AttributeError, IndexError, TypeError):
            return None

    def set(self, key: str, value: Any) -> None:
        if self._source == ConfigSource.DEFAULT:
            raise ValueError("Cannot modify the default configuration")

        current_value = self.get(key)
        if current_value is None:
            raise KeyError(f"Configuration key '{key}' does not exist")

        current_type = type(current_value)  # type: ignore
        new_type = type(value)  # type: ignore

        # Special case: tuples and lists are interchangeable (JSON doesn't have tuples)
        types_compatible = current_type == new_type or (
            current_type in (tuple, list) and new_type in (tuple, list)
        )

        if not types_compatible:
            raise TypeError(
                f"Type mismatch for key '{key}': "
                f"expected {current_type.__name__}, got {new_type.__name__}"
            )

        keys = key.split(".")
        config_dict = self._config.model_dump()

        current = config_dict
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]

        current[keys[-1]] = value

        self._save_config_file(config_dict)

    def list(self) -> Dict[str, Any]:
        if self._source == ConfigSource.DEFAULT:
            return json.loads(DEFAULT_CONFIG_BYTES)

        path = self.source_path
        if not path or not path.exists():
            raise FileNotFoundError(
                f"Configuration file not found at {path}. "
                f"Use 'init' command to create it."
            )

        return self._config.model_dump()

    def init(self) -> None:
        if self._source == ConfigSource.DEFAULT:
            raise ValueError("Cannot initialize the default configuration")

        path = self.requested_source_path
        if path and not path.exists():
            default_config = json.loads(DEFAULT_CONFIG_BYTES)
            self._save_config_file(default_config)
        elif path and path.exists():
            raise FileExistsError(f"Configuration file already exists at {path}")

    def exists(self) -> bool:
        if self._source == ConfigSource.DEFAULT:
            return True
        path = self.source_path
        return path.exists() if path else False
