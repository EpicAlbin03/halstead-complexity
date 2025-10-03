from __future__ import annotations

import json
from importlib import resources
from pathlib import Path
from typing import Dict

from confz import BaseConfig, FileFormat, FileSource
from platformdirs import user_config_dir
from pydantic import BaseModel, ConfigDict, Field


class MultiLineDelimiter(BaseModel):
    model_config = ConfigDict(frozen=True)

    start: str
    end: str


class LanguageConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    comment: tuple[str, ...] = Field(default_factory=tuple)
    extensions: tuple[str, ...] = Field(default_factory=tuple)
    excluded: tuple[str, ...] = Field(default_factory=tuple)
    keywords: tuple[str, ...] = Field(default_factory=tuple)
    symbols: tuple[str, ...] = Field(default_factory=tuple)
    multi_word_operators: tuple[str, ...] = Field(default_factory=tuple)
    multi_line_delimiters: tuple[MultiLineDelimiter, ...] = Field(default_factory=tuple)


def _get_default_config_bytes() -> bytes:
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


DEFAULT_CONFIG_BYTES = _get_default_config_bytes()


class Config(BaseConfig):
    default_language: str
    braces_single_operator: bool
    languages: Dict[str, LanguageConfig]

    CONFIG_SOURCES = [
        FileSource(file=DEFAULT_CONFIG_BYTES, format=FileFormat.JSON),
        FileSource(
            file=user_config_dir(appname="halstead-complexity/config.json"),
            optional=True,
        ),
        FileSource(file=Path.cwd() / "hc_config.json", optional=True),
    ]
