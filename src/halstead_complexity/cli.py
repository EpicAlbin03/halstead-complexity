import tomllib
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer

from halstead_complexity import __app_name__, __version__, config
from halstead_complexity.analysis import Analyzer, format_summary

app = typer.Typer()
config_app = typer.Typer(help=config.CONFIG_HELP_TEXT)
app.add_typer(config_app, name="config")


def _resolve_config_path(path: Optional[Path], local: bool) -> Path:
    if path is not None:
        return path
    return config.local_config_path() if local else config.global_config_path()


def _load_config_data(path: Path) -> Dict[str, Any]:
    if path.exists():
        return config.read_config(path)
    return config.default_config()


def _parse_literal(raw: str) -> Any:
    try:
        return tomllib.loads(f"value = {raw}\n")["value"]
    except Exception:
        try:
            return tomllib.loads(f'value = "{raw}"\n')["value"]
        except Exception:
            return raw


def _build_overrides(pairs: List[str]) -> Dict[str, Any]:
    overrides: Dict[str, Any] = {}
    for pair in pairs:
        if "=" not in pair:
            raise typer.BadParameter(
                "Overrides must be in KEY=VALUE form", param_hint="--set"
            )
        key, raw_value = pair.split("=", 1)
        segments = config.split_key(key)
        if not segments:
            raise typer.BadParameter(
                "Override key must not be empty", param_hint="--set"
            )
        value = _parse_literal(raw_value)
        config.set_nested_value(overrides, segments, value)
    return overrides


@app.command()
def init(
    local: bool = typer.Option(
        False,
        "--local",
        help="Create the configuration in the current directory instead of the global config directory.",
    ),
    path: Optional[Path] = typer.Option(
        None,
        "--path",
        resolve_path=True,
        help="Write the configuration to a custom path.",
    ),
    overwrite: bool = typer.Option(
        False,
        "--overwrite",
        help="Overwrite an existing configuration file without prompting.",
    ),
) -> None:
    """Create a configuration file interactively."""

    target_path = _resolve_config_path(path, local)
    defaults = config.default_config()
    default_language_default = defaults.get("default_language", "") or "python"
    default_language = typer.prompt(
        "Default language", default=default_language_default
    ).strip()
    if not default_language:
        default_language = default_language_default
    paired_default = (
        defaults.get("languages", {})
        .get(default_language_default, {})
        .get("paired_delimiters_single_operator", False)
    )
    paired = typer.confirm(
        "Treat paired delimiters as a single operator?",
        default=bool(paired_default),
    )

    if target_path.exists() and not overwrite:
        if not typer.confirm(
            f"{target_path} already exists. Overwrite?", default=False
        ):
            typer.echo("Aborted")
            raise typer.Exit(1)

    data = config.default_config()
    data["default_language"] = default_language
    try:
        language_entry = data["languages"][default_language]
    except KeyError as error:
        typer.secho(
            f"Language '{default_language}' is not defined in defaults.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1) from error
    language_entry["paired_delimiters_single_operator"] = paired

    config.write_config(target_path, data)
    typer.secho(f"Config file written to {target_path}", fg=typer.colors.GREEN)


@app.command()
def analyze(
    target: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=True,
        readable=True,
        resolve_path=True,
        help="File or directory to analyze.",
    ),
    language: Optional[str] = typer.Option(
        None,
        "--language",
        "-l",
        help="Override the language defined in the config.",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        resolve_path=True,
        help="Write the analysis report to a text file instead of stdout.",
    ),
    config_path: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        resolve_path=True,
        help="Path to a config file. Defaults to the user config directory.",
    ),
    silence: bool = typer.Option(
        False,
        "--silence",
        help="Suppress standard output messages.",
    ),
    set_values: List[str] = typer.Option(
        [],
        "--set",
        help="Override configuration values for this run using KEY=VALUE (repeatable).",
    ),
) -> None:
    overrides: Dict[str, Any] = {}
    if set_values:
        overrides = _build_overrides(set_values)

    project_root = target if target.is_dir() else target.parent
    project_config = config.local_config_path(project_root)

    if config_path is None:
        global_path = config.global_config_path()
        if not project_config.exists() and not global_path.exists():
            config.write_config(global_path, config.default_config())
            typer.secho(
                f"Created default configuration at {global_path}",
                fg=typer.colors.YELLOW,
            )

    try:
        app_config = config.load_app_config(
            config_path,
            project_path=project_config,
            overrides=overrides,
        )
    except Exception as error:
        typer.secho(f"Failed to load config: {error}", fg=typer.colors.RED)
        raise typer.Exit(1) from error

    analyzer = Analyzer(app_config)
    try:
        summary = analyzer.analyze(target, language_name=language)
    except Exception as error:
        typer.secho(f"Analysis failed: {error}", fg=typer.colors.RED)
        raise typer.Exit(1) from error

    report = format_summary(summary)

    if output is not None:
        try:
            parent = output.parent
            if parent and not parent.exists():
                parent.mkdir(parents=True, exist_ok=True)
            output.write_text(report, encoding="utf-8")
        except OSError as error:
            typer.secho(f"Failed to write output file: {error}", fg=typer.colors.RED)
            raise typer.Exit(1) from error
        if not silence:
            typer.secho(f"Analysis written to {output}", fg=typer.colors.GREEN)
    elif not silence:
        typer.echo(report)


@config_app.command("get")
def config_get(
    key: str = typer.Argument(..., help="Configuration key in dotted notation."),
    config_path: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        resolve_path=True,
        help="Path to a configuration file.",
    ),
    local: bool = typer.Option(
        False,
        "--local",
        help="Read from the project-local configuration.",
    ),
) -> None:
    path = _resolve_config_path(config_path, local)
    data = _load_config_data(path)
    segments = config.split_key(key)
    try:
        value = config.get_nested_value(data, segments)
    except KeyError:
        typer.secho(f"Unknown configuration key '{key}'", fg=typer.colors.RED)
        raise typer.Exit(1)
    typer.echo(value)


@config_app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Configuration key in dotted notation."),
    value: str = typer.Argument(..., help="New value for the key."),
    config_path: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        resolve_path=True,
        help="Path to a configuration file.",
    ),
    local: bool = typer.Option(
        False,
        "--local",
        help="Modify the project-local configuration.",
    ),
) -> None:
    path = _resolve_config_path(config_path, local)
    data = _load_config_data(path)
    parsed_value = _parse_literal(value)
    try:
        config.set_nested_value(data, config.split_key(key), parsed_value)
    except ValueError as error:
        typer.secho(str(error), fg=typer.colors.RED)
        raise typer.Exit(1) from error
    config.write_config(path, data)
    typer.secho(f"Updated {key} in {path}", fg=typer.colors.GREEN)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"{__app_name__} v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show the application's version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    return
