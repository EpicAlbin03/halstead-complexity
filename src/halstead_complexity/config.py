from __future__ import annotations

import tomllib
from copy import deepcopy
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Mapping,
    MutableMapping,
    Optional,
    Sequence,
    Union,
    cast,
)

import tomli_w  # type: ignore[import]
import typer
from confz import BaseConfig, DataSource
from pydantic import BaseModel, Field, field_validator

from halstead_complexity import __app_name__

CONFIG_FILENAME = "hc-config.toml"
CONFIG_DIR_PATH = Path(typer.get_app_dir(__app_name__))
DEFAULT_CONFIG_PATH = Path(__file__).with_name("config_defaults.toml")
PathLike = Union[str, Path]


def _load_default_config() -> dict[str, Any]:
    with DEFAULT_CONFIG_PATH.open("rb") as handle:
        data = tomllib.load(handle)
    if not isinstance(data, dict):
        raise ValueError("Default configuration must be a TOML table")
    return cast(dict[str, Any], data)


DEFAULT_CONFIG_DATA: dict[str, Any] = _load_default_config()


def default_config() -> dict[str, Any]:
    """Return a deep copy of the bundled default configuration."""

    return deepcopy(DEFAULT_CONFIG_DATA)


def global_config_path() -> Path:
    return CONFIG_DIR_PATH / CONFIG_FILENAME


def local_config_path(base: Optional[Path] = None) -> Path:
    root = base or Path.cwd()
    return root / CONFIG_FILENAME


def _normalize_for_toml(value: Any) -> Any:
    if isinstance(value, dict):
        mapping = cast(Dict[Any, Any], value)
        return {str(key): _normalize_for_toml(val) for key, val in mapping.items()}
    if isinstance(value, tuple):
        items = cast(tuple[Any, ...], value)
        return [_normalize_for_toml(item) for item in items]
    if isinstance(value, list):
        items = cast(List[Any], value)
        return [_normalize_for_toml(item) for item in items]
    if isinstance(value, set):
        items = list(cast(set[Any], value))
        return [_normalize_for_toml(item) for item in items]
    if isinstance(value, frozenset):
        items = list(cast(frozenset[Any], value))
        return [_normalize_for_toml(item) for item in items]
    if is_dataclass(value) and not isinstance(value, type):
        return _normalize_for_toml(asdict(value))
    return value


def _coerce_path(path: PathLike) -> Path:
    return path if isinstance(path, Path) else Path(path)


def _merge_config_data(
    base: Mapping[str, Any], override: Mapping[str, Any]
) -> dict[str, Any]:
    result: dict[str, Any] = deepcopy(dict(base))
    for key, value in override.items():
        existing = result.get(key)
        if isinstance(existing, Mapping) and isinstance(value, Mapping):
            result[key] = _merge_config_data(
                cast(Mapping[str, Any], existing), cast(Mapping[str, Any], value)
            )
            continue
        result[key] = deepcopy(value)
    return result


def write_config(path: PathLike, data: Mapping[str, Any]) -> None:
    output_path = _coerce_path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    normalized = _normalize_for_toml(dict(data))
    output_path.write_text(tomli_w.dumps(normalized), encoding="utf-8")


def read_config(path: PathLike) -> dict[str, Any]:
    input_path = _coerce_path(path)
    with input_path.open("rb") as handle:
        payload = tomllib.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("Configuration file must contain a TOML table at root")
    return cast(dict[str, Any], payload)


def ensure_config_file(path: PathLike) -> None:
    target_path = _coerce_path(path)
    if target_path.exists():
        return
    write_config(target_path, DEFAULT_CONFIG_DATA)


def split_key(path: str) -> List[str]:
    return [segment for segment in path.split(".") if segment]


def set_nested_value(
    mapping: MutableMapping[str, Any], key: Iterable[str], value: Any
) -> None:
    iterator = iter(key)
    current = mapping
    parts = list(iterator)
    if not parts:
        raise ValueError("Key must not be empty")
    for segment in parts[:-1]:
        if segment not in current or not isinstance(current[segment], MutableMapping):
            current[segment] = {}
        current = current[segment]
    current[parts[-1]] = value


def get_nested_value(mapping: Mapping[str, Any], key: Iterable[str]) -> Any:
    segments = list(key)
    current: Any = mapping
    for segment in segments:
        if not isinstance(current, Mapping) or segment not in current:
            raise KeyError(".".join(segments))
        current = current[segment]
    return current


@dataclass(frozen=True)
class MultilineDelimiter:
    start: str
    end: str


@dataclass(frozen=True)
class LanguageDefinition:
    name: str
    comment_markers: tuple[str, ...]
    excluded: tuple[str, ...]
    keywords: frozenset[str]
    symbols: frozenset[str]
    file_extensions: tuple[str, ...]
    operand_node_types: tuple[str, ...]
    statement_node_types: tuple[str, ...]
    parser_module: Optional[str]
    multiline_delimiters: tuple[MultilineDelimiter, ...]
    paired_delimiters_single_operator: bool = False

    @property
    def operators(self) -> frozenset[str]:
        return frozenset((*self.keywords, *self.symbols))


class MultilineDelimiterConfig(BaseModel):
    start: str
    end: str


class LanguageConfig(BaseModel):
    comment: tuple[str, ...] = Field(alias="comment")
    extensions: tuple[str, ...]
    excluded: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()
    symbols: tuple[str, ...] = ()
    operand_node_types: tuple[str, ...]
    statement_node_types: tuple[str, ...]
    parser_module: Optional[str] = None
    multiline_delimiters: tuple[MultilineDelimiterConfig, ...] = ()
    paired_delimiters_single_operator: bool = False

    @field_validator("multiline_delimiters", mode="before")
    @classmethod
    def _coerce_multiline_delimiters(cls, value: Any) -> Any:
        if value is None:
            return ()
        if isinstance(value, Mapping):
            return cast(dict[str, Any], dict(value))
        if not isinstance(value, Iterable) or isinstance(value, (str, bytes)):
            raise TypeError("multiline_delimiters must be a sequence")

        coerced: list[dict[str, str]] = []
        for item in value:
            if isinstance(item, Mapping):
                mapping_item = cast(Mapping[str, Any], item)
                start = str(mapping_item.get("start", ""))
                end = str(mapping_item.get("end", ""))
            elif isinstance(item, Sequence) and not isinstance(item, (str, bytes)):
                sequence_item = cast(Sequence[Any], item)
                if len(sequence_item) != 2:
                    raise TypeError(
                        "Each multiline delimiter sequence must contain exactly two items"
                    )
                start = str(sequence_item[0])
                end = str(sequence_item[1])
            else:
                raise TypeError(
                    "Each multiline delimiter must be a mapping with 'start' and 'end' keys or a 2-item sequence"
                )
            coerced.append({"start": start, "end": end})
        return coerced


class AppConfigModel(BaseConfig):
    default_language: Optional[str] = None
    languages: Dict[str, LanguageConfig]


@dataclass
class AppConfig:
    languages: Dict[str, LanguageDefinition]
    default_language: Optional[str]

    def language(self, name: str) -> LanguageDefinition:
        try:
            return self.languages[name]
        except KeyError as error:
            raise KeyError(f"Unknown language '{name}' in configuration") from error

    def language_for_extension(self, suffix: str) -> Optional[LanguageDefinition]:
        normalized = suffix if suffix.startswith(".") else f".{suffix}"
        for definition in self.languages.values():
            if normalized in definition.file_extensions:
                return definition
        return None

    def excluded_names(self) -> frozenset[str]:
        return frozenset(
            name
            for definition in self.languages.values()
            for name in definition.excluded
        )


def _language_from_config(name: str, config: LanguageConfig) -> LanguageDefinition:
    return LanguageDefinition(
        name=name,
        comment_markers=tuple(config.comment),
        excluded=tuple(config.excluded),
        keywords=frozenset(config.keywords),
        symbols=frozenset(config.symbols),
        file_extensions=tuple(
            extension if extension.startswith(".") else f".{extension}"
            for extension in config.extensions
        ),
        operand_node_types=tuple(config.operand_node_types),
        statement_node_types=tuple(config.statement_node_types),
        parser_module=config.parser_module,
        multiline_delimiters=tuple(
            MultilineDelimiter(start=item.start, end=item.end)
            for item in config.multiline_delimiters
        ),
        paired_delimiters_single_operator=config.paired_delimiters_single_operator,
    )


def load_app_config(
    path: Optional[Path] = None,
    *,
    project_path: Optional[Path] = None,
    overrides: Optional[Mapping[str, Any]] = None,
) -> AppConfig:
    config_data: Mapping[str, Any] = default_config()

    if path is not None:
        resolved_path = _coerce_path(path)
        if not resolved_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {resolved_path}")
        config_data = _merge_config_data(config_data, read_config(resolved_path))
    else:
        global_path = global_config_path()
        if global_path.exists():
            config_data = _merge_config_data(config_data, read_config(global_path))

        effective_project_path = (
            _coerce_path(project_path)
            if project_path is not None
            else local_config_path()
        )
        if effective_project_path.exists():
            config_data = _merge_config_data(
                config_data, read_config(effective_project_path)
            )

    if overrides:
        config_data = _merge_config_data(config_data, overrides)

    model = AppConfigModel(config_sources=[DataSource(data=config_data)])
    default_language = model.default_language
    if default_language is not None and default_language not in model.languages:
        raise ValueError(
            f"Default language '{default_language}' is not defined in configuration"
        )
    languages = {
        name: _language_from_config(name, config)
        for name, config in model.languages.items()
    }
    return AppConfig(languages=languages, default_language=default_language)


def describe_config(defaults: Optional[Mapping[str, Any]] = None) -> str:
    data = defaults or DEFAULT_CONFIG_DATA
    lines: list[str] = ["Configuration keys with defaults:"]

    def _walk(prefix: str, value: Any) -> None:
        if isinstance(value, Mapping):
            for key, nested in value.items():
                new_prefix = f"{prefix}.{key}" if prefix else key
                _walk(new_prefix, nested)
        else:
            lines.append(f"  - {prefix}: {value}")

    _walk("", data)
    return "\n".join(lines)


CONFIG_HELP_TEXT = describe_config()
